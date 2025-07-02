import discord
from discord.ext import commands
import os
from keep_alive import keep_alive  # 保活功能

# Debug 確認是否有載入環境變數
print("[DEBUG] TEXT_CHANNEL_ID =", os.getenv("TEXT_CHANNEL_ID"))

# 從環境變數中讀取 Token 和頻道 ID
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("TEXT_CHANNEL_ID"))

# 設定必要的 Bot 權限
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

# 建立 Bot 實例
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot 上線：{bot.user}")


@bot.event
async def on_voice_state_update(member, before, after):
    # 偵測使用者加入語音頻道
    if before.channel is None and after.channel is not None:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(
                f"🎧 **{member.display_name}** 加入了語音頻道 **{after.channel.name}**"
            )


# 啟動保活伺服器
keep_alive()

# 啟動 Discord Bot
bot.run(TOKEN)
