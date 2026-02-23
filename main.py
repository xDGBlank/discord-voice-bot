import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive

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
intents.message_content = True  # 解決缺少特權訊息內容意圖的警告

# 建立 Bot 實例
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot 上線：{bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    guild = member.guild

    if before.channel != after.channel:
        if before.channel and after.channel:
            # --- 判斷：移動語音頻道 ---
            await asyncio.sleep(0.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=1):
                    # 加入 entry.target 的防呆檢查
                    if entry.target and entry.target.id == member.id:
                        time_diff = discord.utils.utcnow() - entry.created_at
                        if time_diff.total_seconds() < 5:
                            executor = entry.user
            except discord.Forbidden:
                print("[警告] 機器人缺少『檢視審計日誌』權限！")

            if executor and executor.id != member.id:
                await channel.send(f"🔀 **{executor.name}** 將 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")
            else:
                await channel.send(f"🔀 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")

        elif after.channel:
            # --- 判斷：加入語音頻道 ---
            await channel.send(f"🎧 **{member.name}** 加入了語音頻道 **{after.channel.name}**")

        elif before.channel:
            # --- 判斷：離開/被中斷語音頻道 ---
            await asyncio.sleep(0.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=1):
                    # 加入 entry.target 的防呆檢查
                    if entry.target and entry.target.id == member.id:
                        time_diff = discord.utils.utcnow() - entry.created_at
                        if time_diff.total_seconds() < 5:
                            executor = entry.user
            except discord.Forbidden:
                print("[警告] 機器人缺少『檢視審計日誌』權限！")

            if executor:
                await channel.send(f"❌ **{executor.name}** 把 **{member.name}** 踢出了語音頻道 **{before.channel.name}**")
            else:
                await channel.send(f"👋 **{member.name}** 離開了語音頻道 **{before.channel.name}**")

# 啟動保活伺服器
keep_alive()

# 啟動 Discord Bot
bot.run(TOKEN)
