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

# 設定權限 (Intents)
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True  # 必須開啟，才能讀取 NMSL 禁詞

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 戰績統計系統設定 ---
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
        stats[uid] = {"name": user_name, "joins": 0, "moves": 0, "kicks": 0}
    
    stats[uid]["name"] = user_name  # 更新名字
    stats[uid][stat_type] += 1
    save_stats(stats)
# --------------------

@bot.event
async def on_ready():
    print(f"✅ Bot 上線：{bot.user}")

# --- NMSL 禁詞系統 (嚴格判定 + 忽略標點符號) ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. 把訊息轉小寫
    # 2. 只保留英文字母 (過濾掉標點符號、數字、空白、表情符號)
    # 這樣 "N.M.S.L!!!", "nmsl...", " n m s l " 都會變成 "nmsl"
    content = "".join(char for char in message.content.lower() if char.isalpha())

    # 嚴格檢查：過濾後必須「完全等於」nmsl
    # 這樣 "programs list" (變成 programslist) 就會安全通過
    if content == "nmsl":
        try:
            # 設定禁言時間 (10 分鐘)
            duration = timedelta(minutes=10)
            
            # 1. 執行禁言
            await message.author.timeout(discord.utils.utcnow() + duration, reason="使用了禁詞 NMSL")
            
            # 2. 機器人回覆嘲諷 (保留原訊息不刪除)
            await message.reply(f"**就繼續那麼沒素質吧 我們這裡是文明群組 請你離開**\n{message.author.mention}")
            
        except discord.Forbidden:
            await message.channel.send("⚠️權限不足！那你繼續罵吧")
        except Exception as e:
            print(f"[錯誤] {e}")
        return

    # 讓其他的指令 (如 !統計) 能繼續運作
    await bot.process_commands(message)
# -----------------------------------------------

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    guild = member.guild

    # 判斷狀態改變
    if before.channel != after.channel:
        
        # 情況 1：移動頻道 (原本有頻道 -> 後來也有頻道)
        if before.channel and after.channel:
            await asyncio.sleep(1.5)  # 等待日誌生成
            executor = None
            try:
                # 搜尋最近 5 筆「成員移動」紀錄
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    # 條件：發生在 20 秒內 (防止 Discord 合併日誌導致時間不更新) 且 目標頻道正確
                    if time_diff < 20 and entry.extra and entry.extra.channel.id == after.channel.id:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor and executor.id != member.id:
                # 是被別人拉的 -> 幫兇手加分
                update_stat(executor.id, executor.name, "moves")
                await channel.send(f"🔀 **{executor.name}** 將 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")
            else:
                # 是自己走的
                await channel.send(f"🔀 **{member.name}** 從 **{before.channel.name}** 移動到 **{after.channel.name}**")

        # 情況 2：加入頻道 (原本沒頻道 -> 後來有頻道)
        elif after.channel:
            update_stat(member.id, member.name, "joins")
            await channel.send(f"🎧 **{member.name}** 加入了語音頻道 **{after.channel.name}**")

        # 情況 3：離開/被踢出 (原本有頻道 -> 後來沒頻道)
        elif before.channel:
            await asyncio.sleep(1.5)
            executor = None
            try:
                # 搜尋最近 5 筆「成員中斷連線」紀錄
                async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=5):
                    time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                    # 條件：發生在 20 秒內
                    if time_diff < 20:
                        executor = entry.user
                        break
            except Exception as e:
                print(f"[錯誤] {e}")

            if executor:
                # 是被踢的 -> 幫兇手加分
                update_stat(executor.id, executor.name, "kicks")
                await channel.send(f"❌ **{executor.name}** 把 **{member.name}** 踢出了語音頻道 **{before.channel.name}**")
            else:
                # 是自己離開的
                await channel.send(f"👋 **{member.name}** 離開了語音頻道 **{before.channel.name}**")

# --- !統計 指令 ---
@bot.command(name="統計")
async def show_stats(ctx):
    stats = load_stats()
    if not stats:
        await ctx.send("目前還沒有任何戰績紀錄喔！大家快去語音頻道玩吧！")
        return
    
    # 排序並取前 3 名
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

# 啟動保活伺服器 (給 Railway 用)
keep_alive()

# 啟動 Discord Bot
bot.run(TOKEN)
