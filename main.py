import discord
from discord.ext import commands
import os
import asyncio
import json
from datetime import timedelta
from keep_alive import keep_alive

# Debug 確認是否有載入環境變數
print("[DEBUG] TEXT_CHANNEL_ID =", os.getenv("TEXT_CHANNEL_ID"))

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("TEXT_CHANNEL_ID"))

# --- 👑 這是你的專屬 ID ---
OWNER_ID = 553845904424173600
# ------------------------

# 設定權限 (Intents)
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 戰績統計系統設定 ---
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

# === 🤫 新增功能：閉嘴指令 (只有你能用) ===
@bot.command(name="閉嘴")
async def silent_mute(ctx, member: discord.Member):
    # 1. 安全檢查：確認是不是「主人」下令的
    if ctx.author.id != OWNER_ID:
        return # 如果不是你，機器人直接無視

    # 2. 毀屍滅跡：立刻刪除你的指令訊息
    try:
        await ctx.message.delete()
    except:
        pass

    # 3. 執行禁言：設定 10 分鐘
    try:
        duration = timedelta(minutes=10)
        await member.timeout(discord.utils.utcnow() + duration, reason="主人下令：太吵了")
        
        # 4. 機器人代替你發言 (讓你看起來像個幕後黑手)
        await ctx.send(f"🔇 **{member.mention}** 吵死了，給我閉嘴反省 10 分鐘！")
        
    except discord.Forbidden:
        # 只有你看得到的悄悄話 (如果對方權限比機器人高)
        await ctx.send("🔪 禁言失敗！我的權限不夠動他 (可能他是管理員)。", delete_after=5)
# ==========================================

# === 🗣️ 功能：替身說話/回覆 (只有你能用) ===
@bot.command(name="說")
async def puppet_say(ctx, *, content):
    if ctx.author.id != OWNER_ID:
        return

    try:
        await ctx.message.delete()
    except:
        pass

    if ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        await ref_msg.reply(content)
    else:
        await ctx.send(content)
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

@bot.command(name="統計")
async def show_stats(ctx):
    stats = load_stats()
    if not stats:
        await ctx.send("目前還沒有任何戰績紀錄喔！大家快去語音頻道玩吧！")
        return
    
    top_joins = sorted(stats.values(), key=lambda x: x["joins"], reverse=True)[:3]
    top_moves = sorted(stats.values(), key=lambda x: x["moves"], reverse=True)[:3]
    top_kicks = sorted(stats.values(), key=lambda x: x["kicks"], reverse=True)[:3]

    embed = discord.Embed(title="📊 群組語音戰績排行榜", color=discord.Color.gold())
    
    join_text = "\n".join([f"🥇 {u['name']}: {u['joins']} 次" for u in top_joins if u['joins'] > 0]) or "目前從缺"
    move_text = "\n".join([f"🥇 {u['name']}: {u['moves']} 次" for u in top_moves if u['moves'] > 0]) or "目前從缺"
    kick_text = "\n".join([f"🥇 {u['name']}: {u['kicks']} 次" for u in top_kicks if u['kicks'] > 0]) or "目前從缺"

    embed.add_field(name="🎧 最常加入頻道 (駐站王)", value=join_text, inline=False)
    embed.add_field(name="🔀 最愛當搬運工 (拖曳別人)", value=move_text, inline=False)
    embed.add_field(name="❌ 最無情踢人", value=kick_text, inline=False)

    await ctx.send(embed=embed)

keep_alive()
bot.run(TOKEN)
