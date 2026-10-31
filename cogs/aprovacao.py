import asyncio
import io
import json
import re
import discord
from discord.ext import commands
import config
import core
import db
import fivemanage
import render
from cogs.sync import sync_member_rank

_DOC_ID_RE = re.compile(r"DocID:\s*(\d+)")


def _extract_doc_id(message: discord.Message | None) -> int | None:
    if not message or not message.embeds:
        return None
    footer = (message.embeds[0].footer and message.embeds[0].footer.text) or ""
    m = _DOC_ID_RE.search(footer)
    return int(m.group(1)) if m else None


async def finalize_approved_document(bot: commands.Bot, doc: dict) -> dict:
    """Renders final PDF/PNG, uploads PNG to Fivemanage, updates DB, and DMs the issuing officer."""
    pdf_bytes, png_bytes = await asyncio.to_thread(render.render_document_bundle, doc)
    ctrl = doc["control_no"]
    png_url = None
    try:
        png_url = await fivemanage.upload_png(png_bytes, f"{ctrl}.png")
    except Exception:
        png_url = None

    if png_url:
        with db.connect() as conn:
            conn.execute("UPDATE documents SET png_url = ? WHERE id = ?", (png_url, doc["id"]))
        doc["png_url"] = png_url

    # Notify issuing officer via DM
    try:
        user = await bot.fetch_user(int(doc["issuer_discord_id"]))
        snap = json.loads(doc["template_snapshot"]) if isinstance(doc["template_snapshot"], str) else doc["template_snapshot"]
        verify_link = f"{config.SITE_URL}/verify.html?n={ctrl}"
        emb = discord.Embed(
            title=f"✅ Document Approved — {ctrl}",
            description=(
                f"Your **{snap['name']}** has been counter-signed by **{doc['approver_rank']} {doc['approver_name']}** "
                f"(Badge #{doc['approver_badge']})."
            ),
            color=0x145A32,
        )
        emb.add_field(name="Control Number", value=f"`{ctrl}`", inline=True)
        emb.add_field(name="Public Verification", value=f"[Verify Record]({verify_link})", inline=True)
        if png_url:
            emb.add_field(name="Fivemanage Image Link (DOJ Delivery)", value=png_url, inline=False)
            emb.set_image(url=png_url)

        files = [discord.File(io.BytesIO(pdf_bytes), filename=f"{ctrl}.pdf")]
        if not png_url:
            files.append(discord.File(io.BytesIO(png_bytes), filename=f"{ctrl}.png"))
            emb.set_image(url=f"attachment://{ctrl}.png")
        await user.send(embed=emb, files=files)
    except Exception:
        pass

    return doc


async def post_draft_to_approval_channel(bot: commands.Bot, doc: dict) -> None:
    if not config.APPROVAL_CHANNEL_ID:
        return
    ch = bot.get_channel(config.APPROVAL_CHANNEL_ID)
    if not ch:
        try:
            ch = await bot.fetch_channel(config.APPROVAL_CHANNEL_ID)
        except Exception:
            return

    _, png_bytes = await asyncio.to_thread(render.render_document_bundle, doc)
    snap = json.loads(doc["template_snapshot"]) if isinstance(doc["template_snapshot"], str) else doc["template_snapshot"]
    req_rank = "Commander+" if snap.get("category") == "doj" else "Corporal+"

    emb = discord.Embed(
        title=f"📋 Pending Command Approval — [{snap['code']}] {snap['name']}",
        description=(
            f"**Submitting Officer:** {doc['issuer_rank']} {doc['issuer_name']} (Badge #{doc['issuer_badge']})\n"
            f"**Category:** `{'DOJ Judicial Filing' if snap.get('category') == 'doj' else 'Internal Record'}`\n"
            f"**Required Approving Rank:** `{req_rank}`"
        ),
        color=0xA8842A,
    )
    emb.set_image(url=f"attachment://draft_{doc['id']}.png")
    emb.set_footer(text=f"DocID: {doc['id']} · Unified Police Department Records")

    file = discord.File(io.BytesIO(png_bytes), filename=f"draft_{doc['id']}.png")
    msg = await ch.send(embed=emb, file=file, view=PersistentApprovalView(bot))
    with db.connect() as conn:
        conn.execute("UPDATE documents SET approval_msg_id = ? WHERE id = ?", (str(msg.id), doc["id"]))


class RejectReasonModal(discord.ui.Modal, title="Reject Document Draft"):
    reason = discord.ui.TextInput(
        label="Reason for Rejection / Corrections Needed",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=600,
        placeholder="Specify the missing probable cause facts or statutory corrections required...",
    )

    def __init__(self, bot: commands.Bot, doc_id: int, approver: dict):
        super().__init__()
        self.bot = bot
        self.doc_id = doc_id
        self.approver = approver

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            doc = await asyncio.to_thread(core.reject_document, self.doc_id, self.approver, str(self.reason.value))
        except Exception as e:
            await interaction.followup.send(f"❌ Could not reject document: {e}", ephemeral=True)
            return

        if interaction.message and interaction.message.embeds:
            emb = interaction.message.embeds[0]
            emb.title = f"❌ Rejected — Doc #{doc['id']}"
            emb.color = 0x9E1B1B
            emb.add_field(
                name="Rejected By",
                value=f"{self.approver['rank_name']} {self.approver['rp_name']} (#{self.approver['badge']})",
                inline=False,
            )
            emb.add_field(name="Reason", value=str(self.reason.value), inline=False)
            await interaction.message.edit(embed=emb, view=None)

        try:
            user = await self.bot.fetch_user(int(doc["issuer_discord_id"]))
            await user.send(
                f"❌ Your draft **#{doc['id']} ({doc['template_code']})** was rejected by "
                f"**{self.approver['rank_name']} {self.approver['rp_name']}**.\n"
                f"**Reason:** {self.reason.value}"
            )
        except Exception:
            pass

        await interaction.followup.send(f"Document #{doc['id']} marked as REJECTED.", ephemeral=True)


class PersistentApprovalView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _resolve_approver(self, interaction: discord.Interaction) -> tuple[int | None, dict | None]:
        doc_id = _extract_doc_id(interaction.message)
        if not doc_id:
            await interaction.response.send_message("❌ Could not identify Document ID from message.", ephemeral=True)
            return None, None
        if isinstance(interaction.user, discord.Member):
            await asyncio.to_thread(sync_member_rank, interaction.user)
        approver = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not approver or approver.get("status") != "active":
            await interaction.response.send_message(
                "❌ Your officer profile is not active or admitted in the UPD Registry.", ephemeral=True
            )
            return None, None
        doc = await asyncio.to_thread(core.get_document_full, doc_id)
        if not doc:
            await interaction.response.send_message("❌ Document not found.", ephemeral=True)
            return None, None
        if not core.can_approve(approver, doc):
            await interaction.response.send_message(
                "❌ Patente insuficiente para contra-assinar este documento (ou autoaprovação restrita ao High Command).",
                ephemeral=True,
            )
            return None, None
        return doc_id, approver

    @discord.ui.button(
        label="Approve & Counter-Sign",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="upd:approve_doc",
    )
    async def approve_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        doc_id, approver = await self._resolve_approver(interaction)
        if not doc_id or not approver:
            return
        await interaction.response.defer(ephemeral=True)
        try:
            doc = await asyncio.to_thread(core.approve_document, doc_id, approver)
            doc = await finalize_approved_document(self.bot, doc)
        except Exception as e:
            await interaction.followup.send(f"❌ Error approving document: {e}", ephemeral=True)
            return

        if interaction.message and interaction.message.embeds:
            emb = interaction.message.embeds[0]
            emb.title = f"✅ APPROVED — {doc['control_no']}"
            emb.color = 0x145A32
            emb.add_field(
                name="Counter-Signed By",
                value=f"{doc['approver_rank']} {doc['approver_name']} (Badge #{doc['approver_badge']})",
                inline=True,
            )
            if doc.get("png_url"):
                emb.add_field(name="Fivemanage URL", value=doc["png_url"], inline=False)
            await interaction.message.edit(embed=emb, view=None)

        await interaction.followup.send(
            f"✅ Approved as **{doc['control_no']}**. Final PNG/PDF delivered to the issuing officer.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Reject with Reason",
        style=discord.ButtonStyle.danger,
        emoji="✖️",
        custom_id="upd:reject_doc",
    )
    async def reject_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        doc_id, approver = await self._resolve_approver(interaction)
        if not doc_id or not approver:
            return
        await interaction.response.send_modal(RejectReasonModal(self.bot, doc_id, approver))


class ApprovalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(PersistentApprovalView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(ApprovalCog(bot))
