from dotenv import load_dotenv
load_dotenv()
import discord
from discord.ext import commands
from discord import app_commands
import os
import io
import datetime
import re

TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNEL_ID = 1482585820236877994
CATEGORY_ID = 1487165312247009430
SECOND_CATEGORY_ID = 1492326279914066051
CATEGORY_IDS = [CATEGORY_ID, SECOND_CATEGORY_ID]
TRANSCRIPT_CHANNEL_ID = 1487292108141363271
DONE_CATEGORY_ID = 1482587038292119634 
ADMIN_ROLE_ID = 1482585902676181073 

MEMBER_ROLE_ID = 1482586134478589973
BOT_ROLE_ID = 1486847024484716634
REACTION_CHANNEL_ID = 1486123558873727078

BANNER_URL = "https://cdn.discordapp.com/attachments/1487175323253477597/1487561222558847176/image.png?ex=69c996d9&is=69c84559&hm=ab05c3ca69382968b924b5366c5cddcdd1a941b72097086df061294473e373a7&"

order_counter = 1094

async def create_html_transcript(channel: discord.TextChannel):
    html_content = """
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <title>Transcript - {channel_name}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; background-color: #36393f; color: #dcddde; margin: 0; padding: 20px; direction: rtl; text-align: right; }}
            .container {{ max-width: 800px; margin: auto; background-color: #36393f; padding: 20px; border-radius: 8px; }}
            .message {{ margin-bottom: 15px; display: flex; align-items: flex-start; }}
            .message-avatar {{ width: 40px; height: 40px; border-radius: 50%; margin-left: 10px; margin-right: 0; flex-shrink: 0; }}
            .message-content {{ flex-grow: 1; }}
            .message-author {{ font-weight: bold; color: #ffffff; margin-bottom: 2px; }}
            .message-timestamp {{ color: #72767d; font-size: 0.8em; margin-right: 5px; }}
            .message-text {{ color: #dcddde; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }}
            .header {{ text-align: center; margin-bottom: 30px; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 2em; }}
            .header p {{ margin: 5px 0; color: #72767d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Transcript of #{channel_name}</h1>
                <p>Created: {created_at}</p>
            </div>
    """
    
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(msg)

    for message in messages:
        avatar_url = message.author.display_avatar.url
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author_name = message.author.display_name
        content = message.clean_content.replace("\n", "<br>")

        html_content += f"""
            <div class="message">
                <img class="message-avatar" src="{avatar_url}" alt="{author_name}">
                <div class="message-content">
                    <span class="message-author">{author_name}</span>
                    <span class="message-timestamp">{timestamp}</span>
                    <div class="message-text">{content}</div>
                </div>
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """
    return html_content.format(channel_name=channel.name, created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

async def send_transcript(channel: discord.TextChannel, creator: discord.Member, order_taker: discord.Member):
    html_transcript = await create_html_transcript(channel)
    transcript_file = discord.File(io.BytesIO(html_transcript.encode("utf-8")), filename=f"transcript-{channel.name}.html")

    transcript_channel = channel.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
    if transcript_channel and isinstance(transcript_channel, discord.TextChannel):
        await transcript_channel.send(f"Transcript for ticket \'{channel.name}\' (Created by {creator.mention}, Taken by {order_taker.mention}):", file=transcript_file)
    else:
        print(f"Error: Transcript channel with ID {TRANSCRIPT_CHANNEL_ID} not found or is not a text channel.")

class TicketControlView(discord.ui.View):
    def __init__(self, creator: discord.Member, order_taker: discord.Member):
        super().__init__(timeout=None)
        self.creator = creator
        self.order_taker = order_taker

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("عذراً، من يملك رتبة الإدارة فقط هو من يمكنه التحكم في التكت.", ephemeral=True)
        return False

    @discord.ui.button(label="Open", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        overwrites = channel.overwrites
        overwrites[self.order_taker] = discord.PermissionOverwrite(send_messages=True, view_channel=True)
        overwrites[self.creator] = discord.PermissionOverwrite(send_messages=True, view_channel=True)
        await channel.edit(overwrites=overwrites)

        await interaction.response.send_message("Ticket has been opened.", ephemeral=True)
        
        original_category = guild.get_channel(CATEGORY_ID)
        if original_category and isinstance(original_category, discord.CategoryChannel):
            new_name = channel.name.replace('done-', '') if channel.name.startswith('done-') else channel.name
            await channel.edit(category=original_category, name=new_name)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        overwrites = channel.overwrites
        overwrites[self.order_taker] = discord.PermissionOverwrite(send_messages=False, view_channel=False)
        overwrites[self.creator] = discord.PermissionOverwrite(send_messages=False, view_channel=False)
        await channel.edit(overwrites=overwrites)
        
        await interaction.response.send_message("Ticket has been closed.", ephemeral=True)
        await send_transcript(channel, self.creator, self.order_taker) 

        done_category = guild.get_channel(DONE_CATEGORY_ID)
        if done_category and isinstance(done_category, discord.CategoryChannel):
            await channel.edit(category=done_category, name=f"done-{channel.name}")

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.grey, custom_id="delete_ticket_button")
    async def delete_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Deleting ticket and creating transcript...", ephemeral=True)
        channel = interaction.channel
        await send_transcript(channel, self.creator, self.order_taker)
        await channel.delete()

class SettingsView(discord.ui.View):
    def __init__(self, creator: discord.Member, order_taker: discord.Member):
        super().__init__(timeout=None)
        self.creator = creator
        self.order_taker = order_taker

    @discord.ui.button(label="Settings", style=discord.ButtonStyle.grey, emoji="🛠️", custom_id="ticket_settings_button")
    async def ticket_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("عذراً، من يملك رتبة الإدارة فقط هو من يمكنه استخدام هذا الزر.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Ticket Management",
            description="Choose an action for the current ticket:",
            color=discord.Color.dark_grey()
        )
        embed.set_image(url=BANNER_URL)
        
        view = TicketControlView(self.creator, self.order_taker)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class OrderView(discord.ui.View):
    def __init__(self, order_name, order_details, image_url, creator, price: str = None, order_id: int = 0):
        super().__init__(timeout=None)
        self.order_name = order_name
        self.order_details = order_details
        self.image_url = image_url
        self.creator = creator
        self.price = price
        self.order_id = order_id

    @discord.ui.button(label="Take Order", style=discord.ButtonStyle.red, emoji="🏷️", custom_id="order_button")
    async def order_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.creator.id:
            await interaction.response.send_message("انت صاحب الاوردر يصاحبي هتطلبه ازاي ", ephemeral=True)
            return

        category = interaction.guild.get_channel(CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Error: Category not found.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.creator: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel_name = f"{self.order_name}"
        new_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"تم إنشاء تكت لطلبك: {new_channel.mention}", ephemeral=True)

        order_embed = discord.Embed(
            title=f"・𝐄𝐋𝐓𝐒𝐋𝐄𝐌𝐀𝐓・",
            description=f"\n```\n{self.order_details}\n```\\n **Price:** {self.price if self.price else 'غير محدد'}",
            color=discord.Color.red()
        )
        order_embed.set_image(url=BANNER_URL)
        if self.image_url:
            order_embed.set_thumbnail(url=self.image_url)
        
        order_embed.set_footer(text="© Rovel Store")
        
        settings_view = SettingsView(self.creator, interaction.user)
        mentions = f"{self.creator.mention} {interaction.user.mention}"
        await new_channel.send(content=mentions, embed=order_embed, view=settings_view)

    @discord.ui.button(label="Settings ", style=discord.ButtonStyle.grey, emoji="🛠️", custom_id="main_settings_button")
    async def main_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("", ephemeral=True)
            return

        embed = discord.Embed(
            title="Order Settings",
            description="Manage the status of this order:",
            color=discord.Color.blue()
        )
        embed.set_image(url=BANNER_URL)
        
        view = discord.ui.View()

        async def open_callback(inter: discord.Interaction):
            for child in self.children:
                if child.custom_id == "order_button":
                    child.disabled = False
            
            orig_embed = interaction.message.embeds[0]
            orig_embed.color = discord.Color.green()
            await interaction.message.edit(embed=orig_embed, view=self)
            await inter.response.send_message("Order has been opened.", ephemeral=True)

        async def close_callback(inter: discord.Interaction):
            for child in self.children:
                if child.custom_id == "order_button":
                    child.disabled = True
                    child.label = "Delivered"
                    child.style = discord.ButtonStyle.red
            
            orig_embed = interaction.message.embeds[0]
            orig_embed.color = discord.Color.red()
            await interaction.message.edit(embed=orig_embed, view=self)
            await inter.response.send_message("Order has been closed and marked as Delivered.", ephemeral=True)

        btn_open = discord.ui.Button(label="Open", style=discord.ButtonStyle.green)
        btn_open.callback = open_callback
        btn_close = discord.ui.Button(label="Close", style=discord.ButtonStyle.red)
        btn_close.callback = close_callback
        
        view.add_item(btn_open)
        view.add_item(btn_close)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

@bot.event
async def on_member_join(member):
    try:
        if member.bot:
            role = member.guild.get_role(BOT_ROLE_ID)
            if role:
                await member.add_roles(role)
        else:
            role = member.guild.get_role(MEMBER_ROLE_ID)
            if role:
                await member.add_roles(role)
    except Exception as e:
        print(f"Error in on_member_join: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == REACTION_CHANNEL_ID:
        try:
            await message.add_reaction("❤️")
            await message.add_reaction("🔥")
        except Exception as e:
            print(f"Error adding reaction: {e}")
    await bot.process_commands(message)

@bot.tree.command(name="neworder", description="إنشاء طلب جديد")
@app_commands.describe(
    name="اسم الطلب",
    details="تفاصيل الطلب",
    image="صورة الطلب (مرفق)",
    price="سعر الطلب (اختياري)"
)
async def neworder(interaction: discord.Interaction, name: str, details: str, image: discord.Attachment = None, price: str = None):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(f" <#{ALLOWED_CHANNEL_ID}>", ephemeral=True)
        return

    global order_counter
    current_order_id = order_counter
    order_counter += 1

    embed = discord.Embed(
        title=f"・𝐄𝐋𝐓𝐒𝐋𝐄𝐌𝐀𝐓・",
        description=f":fsdfasdf: ```\n{details}\n```\n **:fsdfasdf: Price : {price if price else '-'}**",
        color=discord.Color.red()
    )
    
    embed.set_image(url=BANNER_URL) 
    if image:
        embed.set_thumbnail(url=image.url) 
    
    embed.set_footer(text="© Rovel Store")
    
    view = OrderView(name, details, image.url if image else None, interaction.user, price, current_order_id)
    allowed_mentions = discord.AllowedMentions(everyone=True)
    await interaction.response.send_message(content="@everyone", embed=embed, view=view, allowed_mentions=allowed_mentions)

@bot.tree.command(name="add", description="إضافة شخص إلى التكت")
@app_commands.describe(member="الشخص المراد إضافته")
async def add(interaction: discord.Interaction, member: discord.Member):
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("عذراً، لا تملك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
        return

    if not interaction.channel.category or interaction.channel.category_id not in CATEGORY_IDS:
        await interaction.response.send_message("هذا الأمر يعمل فقط داخل الرومات الموجودة في الكاتيجوري المحددة.", ephemeral=True)
        return

    try:
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True)
        await interaction.response.send_message(f"تم إضافة {member.mention} إلى التكت بنجاح.")
    except Exception as e:
        await interaction.response.send_message(f"حدث خطأ أثناء محاولة إضافة العضو: {e}", ephemeral=True)

@bot.tree.command(name="fetch", description="إظهار جميع تكتات مستلم الطلب (Order Taker)")
@app_commands.describe(member="العضو المراد جلب تكتاته")
async def fetch(interaction: discord.Interaction, member: discord.Member):
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("عذراً، لا تملك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
        return

    await interaction.response.defer()
    
    target_user = member
    user_tickets = []
    
    for category_id in CATEGORY_IDS:
        category = interaction.guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            continue

        for channel in category.text_channels:
            async for message in channel.history(limit=1, oldest_first=True):
                mentions = re.findall(r'<@!?(\d+)>', message.content)
                if len(mentions) >= 2:
                    second_mention_id = int(mentions[1])
                    if second_mention_id == target_user.id:
                        user_tickets.append(channel)
                break

    if not user_tickets:
        await interaction.followup.send(f"لا توجد تكتات مستلمة لـ {target_user.mention} في الكاتيجوري المحددة.")
        return

    embed = discord.Embed(
        title=f"Tickets Taken by {target_user.display_name}",
        description=f"إجمالي التكتات المستلمة: **{len(user_tickets)}**\n\n" + "\n".join([f"- {ch.mention} [رابط التكت]({ch.jump_url})" for ch in user_tickets]),
        color=discord.Color.blue()
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text=f"طلب بواسطة {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="rename", description="تغيير اسم الروم")
@app_commands.describe(name="الاسم الجديد للروم")
async def rename(interaction: discord.Interaction, name: str):
    if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("عذراً، لا تملك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
        return

    try:
        old_name = interaction.channel.name
        await interaction.channel.edit(name=name)
        await interaction.response.send_message(f"تم تغيير اسم الروم من `{old_name}` إلى `{name}` بنجاح.")
    except Exception as e:
        await interaction.response.send_message(f"حدث خطأ أثناء محاولة تغيير الاسم: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(TOKEN)
