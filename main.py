import discord
from discord.ext import commands
import os
import asyncio
import json # 新增：用來讀寫統計資料的套件
from keep_alive import keep_alive

# Debug 確認是否有載入環境變數
print("[DEBUG] TEXT_CHANNEL_ID =", os.getenv("TEXT_CHANNEL_ID"))

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("TEXT_CHANNEL_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 統計系統設定 ---
STATS_FILE = "stats.json"

def load_stats():
    """讀取統計資料"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_stats(stats):
    """儲存統計資料"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

def update_stat(user_id, user_name, stat_type):
    """更新某人的特定數值"""
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats:
        # 如果是新來的，幫他建一個乾淨的計分板
        stats[uid] = {"name": user_name, "joins": 0, "moves": 0, "kicks": 0}
    
    stats[uid]["name"] = user_name # 更新名字 (避免有人改名)
    stats[uid][stat_type] += 1
    save_stats(stats)
# --------------------

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
            # --- 移動語音頻道 ---
            await asyncio.sleep(1.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    if time_diff < 5 and entry.extra and entry.extra.channel.id == after.channel.id:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor and executor.id != member.id:
                # 幫動手拉人的人「moves」加 1 分
                update_stat(executor.id, executor.name, "moves")
                await channel.send(f"🔀 **{executor.name}** 將 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")
            else:
                await channel.send(f"🔀 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")

        elif after.channel:
            # --- 加入語音頻道 ---
            # 幫加入的人「joins」加 1 分
            update_stat(member.id, member.name, "joins")
            await channel.send(f"🎧 **{member.name}** 加入了語音頻道 **{after.channel.name}**")

        elif before.channel:
            # --- 離開/被中斷語音頻道 ---
            await asyncio.sleep(1.5)
            executor = None
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    if time_diff < 5:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor:
                # 幫動手踢人的人「kicks」加 1 分
                update_stat(executor.id, executor.name, "kicks")
                await channel.send(f"❌ **{executor.name}** 把 **{member.name}** 踢出了語音頻道 **{before.channel.name}**")
            else:
                await channel.send(f"👋 **{member.name}** 離開了語音頻道 **{before.channel.name}**")

# --- 新增的戰績查詢指令 ---
@bot.command(name="排行")
async def show_stats(ctx):
    stats = load_stats()
    if not stats:
        await ctx.send("目前還沒有任何戰績紀錄喔！大家快去語音頻道玩吧！")
        return
    
    # 幫各個項目進行排名 (取前 3 名)
    top_joins = sorted(stats.values(), key=lambda x: x["joins"], reverse=True)[:3]
    top_moves = sorted(stats.values(), key=lambda x: x["moves"], reverse=True)[:3]
    top_kicks = sorted(stats.values(), key=lambda x: x["kicks"], reverse=True)[:3]

    # 製作漂亮的嵌入訊息 (Embed)
    embed = discord.Embed(title="📊 群組語音戰績排行榜", color=discord.Color.gold())
    
    join_text = "\n".join([f"🥇 {u['name']}: {u['joins']} 次" for u in top_joins if u['joins'] > 0]) or "目前從缺"
    move_text = "\n".join([f"🥇 {u['name']}: {u['moves']} 次" for u in top_moves if u['moves'] > 0]) or "目前從缺"
    kick_text = "\n".join([f"🥇 {u['name']}: {u['kicks']} 次" for u in top_kicks if u['kicks'] > 0]) or "目前從缺"

    embed.add_field(name="🎧 最常加入頻道 (駐站王)", value=join_text, inline=False)
    embed.add_field(name="🔀 最愛當搬運工 (拖曳別人)", value=move_text, inline=False)
    embed.add_field(name="❌ 最無情踢人", value=kick_text, inline=False)

    await ctx.send(embed=embed)

# 啟動保活伺服器
keep_alive()

# 啟動 Discord Bot
bot.run(TOKEN)
