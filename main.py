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
            await asyncio.sleep(3)  # 等待 3 秒，確保 Discord 來得及寫入日誌
            executor = None
            try:
                print(f"\n[DEBUG] --- 發生移動事件：{member.name} 從 {before.channel.name} 到 {after.channel.name} ---")
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    target_name = entry.target.name if entry.target else "未知"
                    print(f"[DEBUG] 翻找日誌 -> 執行者: {entry.user.name}, 目標: {target_name}, 時間差: {time_diff:.1f}秒")
                    
                    if entry.target and entry.target.id == member.id:
                        if time_diff < 15:
                            executor = entry.user
                            print(f"[DEBUG] 成功配對！是 {executor.name} 拉的！")
                            break
            except discord.Forbidden:
                print("[警告] 機器人缺少『檢視審計日誌』權限！")
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor and executor.id != member.id:
                await channel.send(f"🔀 **{executor.name}** 將 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")
            else:
                await channel.send(f"🔀 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")

        elif after.channel:
            # --- 判斷：加入語音頻道 ---
            await channel.send(f"🎧 **{member.name}** 加入了語音頻道 **{after.channel.name}**")

        elif before.channel:
            # --- 判斷：離開/被中斷語音頻道 ---
            await asyncio.sleep(3) # 等待 3 秒
            executor = None
            try:
                print(f"\n[DEBUG] --- 發生離開事件：{member.name} 離開 {before.channel.name} ---")
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    target_name = entry.target.name if entry.target else "未知"
                    print(f"[DEBUG] 翻找日誌 -> 執行者: {entry.user.name}, 目標: {target_name}, 時間差: {time_diff:.1f}秒")
                    
                    if entry.target and entry.target.id == member.id:
                        if time_diff < 15:
                            executor = entry.user
                            print(f"[DEBUG] 成功配對！是 {executor.name} 踢的！")
                            break
            except discord.Forbidden:
                print("[警告] 機器人缺少『檢視審計日誌』權限！")
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor:
                await channel.send(f"❌ **{executor.name}** 把 **{member.name}** 踢出了語音頻道 **{before.channel.name}**")
            else:
                await channel.send(f"👋 **{member.name}** 離開了語音頻道 **{before.channel.name}**")

# 啟動保活伺服器
keep_alive()

# 啟動 Discord Bot
bot.run(TOKEN)
