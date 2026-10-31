import asyncio
import io
import json
import discord
from discord import app_commands
from discord.ext import commands
import config
import core
import db
import render
from cogs.aprovacao import post_draft_to_approval_channel
from cogs.sync import sync_member_rank


class DynamicTemplateModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, officer: dict, template: dict, initial_values: dict | None = None):
        super().__init__(title=f"Issue [{template['code']}] {template['name'][:32]}")
        self.bot = bot
        self.officer = officer
        self.template = template
        self.fields_meta = json.loads(template["fields_json"])[:5]
        self.inputs: dict[str, discord.ui.TextInput] = {}

        for f in self.fields_meta:
            style = discord.TextStyle.paragraph if f.get("type") == "textarea" else discord.TextStyle.short
            ti = discord.ui.TextInput(
                label=f["label"][:45],
                style=style,
                required=bool(f.get("required", True)),
                max_length=min(int(f.get("max_length", 1000)), 4000),
                placeholder=(f.get("placeholder") or "")[:100],
                default=(initial_values or {}).get(f["key"], ""),
            )
            self.inputs[f["key"]] = ti
            self.add_item(ti)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        values = {k: str(inp.value).strip() for k, inp in self.inputs.items()}
        preview_doc = {
            "id": "PREVIEW",
            "control_no": None,
            "template_snapshot": self.template,
            "data_json": values,
            "status": "PENDING",
            "issuer_name": self.officer["rp_name"],
            "issuer_badge": self.officer["badge"],
            "issuer_rank": self.officer.get("rank_name") or "Officer",
            "issuer_division": self.officer.get("division") or "Patrol Division",
        }
        try:
            _, png_bytes = await asyncio.to_thread(render.render_document_bundle, preview_doc)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to render preview: {e}", ephemeral=True)
            return

        emb = discord.Embed(
            title=f"📄 Draft Preview — [{self.template['code']}] {self.template['name']}",
            description=(
                "Review the rendered draft below. Click **Submit for Command Approval** to send it to the "
                "approval queue, or **Edit Fields** to make changes."
            ),
            color=0x111E38,
        )
        emb.set_image(url="attachment://preview.png")
        view = DraftPreviewConfirmView(self.bot, self.officer, self.template, values)
        await interaction.followup.send(
            embed=emb,
            file=discord.File(io.BytesIO(png_bytes), filename="preview.png"),
            view=view,
            ephemeral=True,
        )


class DraftPreviewConfirmView(discord.ui.View):
    def __init__(self, bot: commands.Bot, officer: dict, template: dict, values: dict):
        super().__init__(timeout=600)
        self.bot = bot
        self.officer = officer
        self.template = template
        self.values = values

    @discord.ui.button(label="Submit for Command Approval", style=discord.ButtonStyle.success, emoji="📨")
    async def submit_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            doc = await asyncio.to_thread(core.create_draft, self.officer, self.template["code"], self.values)
            await post_draft_to_approval_channel(self.bot, doc)
        except Exception as e:
            await interaction.followup.send(f"❌ Error submitting draft: {e}", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(
            f"✅ Draft **#{doc['id']} ({self.template['code']})** submitted to Command Staff for counter-signature.",
            ephemeral=True,
        )

    @discord.ui.button(label="Edit Fields", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        await interaction.response.send_modal(
            DynamicTemplateModal(self.bot, self.officer, self.template, initial_values=self.values)
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancel_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Draft cancelled.", embed=None, attachments=[], view=self)


class EmitirCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _template_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if isinstance(interaction.user, discord.Member):
            await asyncio.to_thread(sync_member_rank, interaction.user)
        officer = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM templates WHERE active = 1 ORDER BY code").fetchall()
        choices: list[app_commands.Choice[str]] = []
        for r in rows:
            t = db.row_to_dict(r)
            if officer and not core.can_issue(officer, t):
                continue
            label = f"[{t['code']}] {t['name']} ({'Modal' if t['channel']=='modal' else 'Web Panel'})"
            if not current or current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label[:100], value=t["code"]))
        return choices[:25]

    @app_commands.command(name="emitirdocumento", description="Issue an official UPD document or DOJ judicial filing")
    @app_commands.describe(tipo="Document template code (e.g., SW, AW, CO, SO, FQ, CM)")
    @app_commands.autocomplete(tipo=_template_autocomplete)
    async def emitir_documento(self, interaction: discord.Interaction, tipo: str):
        if isinstance(interaction.user, discord.Member):
            await asyncio.to_thread(sync_member_rank, interaction.user)
        officer = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not officer or officer.get("status") != "active":
            await interaction.response.send_message(
                "❌ Your officer profile is not active yet. Request admission from a Command Administrator.",
                ephemeral=True,
            )
            return

        with db.connect() as conn:
            row = conn.execute("SELECT * FROM templates WHERE code = ? AND active = 1", (tipo.upper(),)).fetchone()
        if not row:
            await interaction.response.send_message(f"❌ Template `{tipo}` not found or inactive.", ephemeral=True)
            return
        template = db.row_to_dict(row)
        if not core.can_issue(officer, template):
            await interaction.response.send_message(
                "❌ Your current rank does not have permission to issue this document type.", ephemeral=True
            )
            return

        fields = json.loads(template["fields_json"])
        if template["channel"] == "modal" and len(fields) <= 5:
            await interaction.response.send_modal(DynamicTemplateModal(self.bot, officer, template))
        else:
            url = f"{config.SITE_URL}/#/emitir/{template['code']}"
            emb = discord.Embed(
                title=f"🌐 Complete Long-Form Filing on UPD Web Portal — [{template['code']}]",
                description=(
                    f"**{template['name']}** contains detailed narrative sections ({len(fields)} fields) "
                    f"with live US-Letter document preview.\n\n"
                    f"👉 **[Open Filing Composer ({template['code']})]({url})**"
                ),
                color=0x111E38,
            )
            await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="meusdocumentos", description="List your recent UPD documents and their approval status")
    async def meus_documentos(self, interaction: discord.Interaction):
        officer = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not officer:
            await interaction.response.send_message("❌ Officer profile not found.", ephemeral=True)
            return
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT id, control_no, template_code, status, png_url, created_at FROM documents WHERE issuer_id = ? ORDER BY id DESC LIMIT 10",
                (officer["id"],),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("You have not issued any documents yet.", ephemeral=True)
            return
        lines = []
        for r in rows:
            ctrl = r["control_no"] or f"Draft #{r['id']}"
            link = f" · [Image]({r['png_url']})" if r["png_url"] else ""
            lines.append(f"• **{ctrl}** (`{r['template_code']}`) — **{r['status']}** · {r['created_at'][:10]}{link}")
        emb = discord.Embed(title="🗂️ Your Recent UPD Documents", description="\n".join(lines), color=0x111E38)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="documento", description="Retrieve the official PDF and Fivemanage link of a document")
    @app_commands.describe(numero="Control number (e.g., UPD-SW-2026-0001) or Draft ID")
    async def obter_documento(self, interaction: discord.Interaction, numero: str):
        officer = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        with db.connect() as conn:
            if numero.isdigit():
                row = conn.execute("SELECT id FROM documents WHERE id = ?", (int(numero),)).fetchone()
            else:
                row = conn.execute("SELECT id FROM documents WHERE control_no = ?", (numero.upper(),)).fetchone()
        if not row:
            await interaction.response.send_message("❌ Document not found.", ephemeral=True)
            return
        doc = await asyncio.to_thread(core.get_document_full, row["id"])
        if not core.can_view_document(officer, doc):
            await interaction.response.send_message("❌ Access denied to this document.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        pdf_bytes, _ = await asyncio.to_thread(render.render_document_bundle, doc)
        ctrl = doc["control_no"] or f"DRAFT-{doc['id']}"
        msg = f"📄 **{ctrl}** — Status: **{doc['status']}**"
        if doc.get("png_url"):
            msg += f"\n🔗 **Fivemanage PNG:** {doc['png_url']}"
        await interaction.followup.send(
            content=msg,
            file=discord.File(io.BytesIO(pdf_bytes), filename=f"{ctrl}.pdf"),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EmitirCog(bot))
