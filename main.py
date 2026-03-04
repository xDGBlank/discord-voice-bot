import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import json
from datetime import timedelta
from keep_alive import keep_alive

# Debug 確認是否有載入環境變數
print("[DEBUG] TEXT_CHANNEL_ID =", os.getenv("TEXT_CHANNEL_ID"))

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("TEXT_CHANNEL_ID"))

# --- 👑 請確認這裡還是你的 ID ---
OWNER_ID = 553845904424173600
# -----------------------------

# 設定權限
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True 

# 這裡我們同時保留 ! 指令，並啟用 app_commands (斜線指令)
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 這一步很重要：把斜線指令同步到 Discord 伺服器
        # 為了讓指令馬上出現，我們這裡執行同步
        await self.tree.sync()
        print("✅ 斜線指令已同步完成！")

bot = MyBot()

# --- 戰績統計系統 ---
STATS_FILE = "stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

def update_stat(user_id, user_name, stat_type):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"name": user_name, "joins": 0, "moves": 0, "kicks": 0}
    stats[uid]["name"] = user_name
    stats[uid][stat_type] += 1
    save_stats(stats)

@bot.event
async def on_ready():
    print(f"✅ Bot 上線：{bot.user}")

# ==========================================
# 🎮 全新：斜線指令區域 (Slash Commands)
# ==========================================

# 1. /說：讓機器人幫你說話
@bot.tree.command(name="說", description="(管理員指令) 讓機器人代替你發出訊息")
@app_commands.describe(content="你想讓機器人說的話")
async def slash_say(interaction: discord.Interaction, content: str):
    # 檢查權限
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 你沒有權限使用此指令。", ephemeral=True)
        return

    # 1. 先回覆你一個「只有你看得到的訊息」，證明指令收到
    # 這就是截圖裡那個「只有您才能看到這個」的效果
    await interaction.response.send_message(f"✅ 【訊息發送成功】\n內容：{content}", ephemeral=True)

    # 2. 機器人在頻道公開說話
    await interaction.channel.send(content)

# 2. /閉嘴：禁言某人 10 分鐘
@bot.tree.command(name="閉嘴", description="(管理員指令) 讓某人閉嘴 10 分鐘")
@app_commands.describe(member="要閉嘴的對象")
async def slash_shut_up(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 你沒有權限使用此指令。", ephemeral=True)
        return

    try:
        duration = timedelta(minutes=10)
        await member.timeout(discord.utils.utcnow() + duration, reason="主人下令：太吵了")
        
        # 回覆你看得到的確認訊息
        await interaction.response.send_message(f"✅ 已成功讓 {member.name} 閉嘴。", ephemeral=True)
        
        # 機器人公開嗆聲
        await interaction.channel.send(f"🔇 **{member.mention}** 吵死了，給我閉嘴反省 10 分鐘！")
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ 權限不足，我無法禁言該使用者。", ephemeral=True)

# 3. /暗殺：偷偷踢出語音
@bot.tree.command(name="暗殺", description="(管理員指令) 偷偷把人踢出語音頻道")
@app_commands.describe(member="暗殺對象")
async def slash_assassinate(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 你沒有權限使用此指令。", ephemeral=True)
        return

    if member.voice:
        try:
            await member.move_to(None)
            # 只有你看得到的成功訊息
            await interaction.response.send_message(f"🔪 暗殺成功！已將 {member.name} 踢出語音。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ 暗殺失敗，權限不足。", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 目標不在語音頻道內。", ephemeral=True)

# 4. /統計：查詢戰績
@bot.tree.command(name="統計", description="查看目前的語音戰績排行榜")
async def slash_stats(interaction: discord.Interaction):
    stats = load_stats()
    if not stats:
        await interaction.response.send_message("目前還沒有任何戰績紀錄喔！", ephemeral=False)
        return
    
    top_joins = sorted(stats.values(), key=lambda x: x["joins"], reverse=True)[:3]
    top_moves = sorted(stats.values(), key=lambda x: x["moves"], reverse=True)[:3]
    top_kicks = sorted(stats.values(), key=lambda x: x["kicks"], reverse=True)[:3]

    embed = discord.Embed(title="📊 群組語音戰績排行榜", color=discord.Color.gold())
    
    join_text = "\n".join([f"🥇 {u['name']}: {u['joins']} 次" for u in top_joins if u['joins'] > 0]) or "目前從缺"
    move_text = "\n".join([f"🥇 {u['name']}: {u['moves']} 次" for u in top_moves if u['moves'] > 0]) or "目前從缺"
    kick_text = "\n".join([f"🥇 {u['name']}: {u['kicks']} 次" for u in top_kicks if u['kicks'] > 0]) or "目前從缺"

    embed.add_field(name="🎧 最常加入頻道", value=join_text, inline=False)
    embed.add_field(name="🔀 最愛當搬運工", value=move_text, inline=False)
    embed.add_field(name="❌ 最無情踢人", value=kick_text, inline=False)

    await interaction.response.send_message(embed=embed)

# ==========================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # NMSL 嚴格判定邏輯
    content = "".join(char for char in message.content.lower() if char.isalpha())

    if content == "nmsl":
        try:
            duration = timedelta(minutes=10)
            await message.author.timeout(discord.utils.utcnow() + duration, reason="使用了禁詞 NMSL")
            await message.reply(f"**就繼續那麼沒素質吧**\n{message.author.mention}")
        except discord.Forbidden:
            await message.channel.send("⚠️ 權限不足！請檢查我的身分組權限！")
        except Exception as e:
            print(f"[錯誤] {e}")
        return

    # 處理傳統指令 (如果有保留的話)
    await bot.process_commands(message)

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
            # 移動
            await asyncio.sleep(1.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    if time_diff < 20 and entry.extra and entry.extra.channel.id == after.channel.id:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor and executor.id != member.id:
                update_stat(executor.id, executor.name, "moves")
                await channel.send(f"🔀 **{executor.name}** 將 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")
            else:
                await channel.send(f"🔀 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")

        elif after.channel:
            # 加入
            update_stat(member.id, member.name, "joins")
            await channel.send(f"🎧 **{member.name}** 加入了語音頻道 **{after.channel.name}**")

        elif before.channel:
            # 離開/踢出
            await asyncio.sleep(1.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    if time_diff < 20:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor:
                update_stat(executor.id, executor.name, "kicks")
                await channel.send(f"❌ **{executor.name}** 把 **{member.name}** 踢出了語音頻道 **{before.channel.name}**")
            else:
                await channel.send(f"👋 **{member.name}** 離開了語音頻道 **{before.channel.name}**")

keep_alive()
bot.run(TOKEN)
