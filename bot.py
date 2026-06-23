import discord
from discord import app_commands
from discord.ext import commands
import random
import os
import json
import aiohttp
import aiofiles
from pathlib import Path

# ตั้งค่า
TOKEN = os.environ.get("TOKEN")
IMAGES_DIR = Path("./images")
IMAGES_INDEX = Path("./images/index.json")

# สร้างโฟลเดอร์ถ้ายังไม่มี
IMAGES_DIR.mkdir(exist_ok=True)

# โหลด/สร้าง index รูปภาพ
def load_images() -> list[dict]:
    if IMAGES_INDEX.exists():
        with open(IMAGES_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_images(images: list[dict]):
    with open(IMAGES_INDEX, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2)

# สร้างบอท
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")
    try:
        synced = await tree.sync()
        print(f"📌 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Error syncing: {e}")

# /random - สุ่มรูปภาพ
@tree.command(name="random", description="สุ่มรูปภาพจากคลัง")
async def random_image(interaction: discord.Interaction):
    images = load_images()

    if not images:
        await interaction.response.send_message(
            "❌ ยังไม่มีรูปภาพในคลัง ใช้ `/add` เพื่ออัปโหลดรูปก่อนนะครับ!",
            ephemeral=True
        )
        return

    chosen = random.choice(images)
    file_path = Path(chosen["path"])

    if not file_path.exists():
        # ลบออกจาก index ถ้าไฟล์หายไป
        images.remove(chosen)
        save_images(images)
        await interaction.response.send_message("⚠️ ไม่พบไฟล์ ลองใหม่อีกครั้งนะครับ", ephemeral=True)
        return

    await interaction.response.send_message(
        f"🎲 สุ่มได้รูป: **{chosen['name']}**",
        file=discord.File(file_path, filename=file_path.name)
    )

    # ตรวจสอบว่าเป็นรูปภาพ
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        await interaction.response.send_message(
            "❌ รองรับเฉพาะไฟล์ภาพ (JPG, PNG, GIF, WEBP) เท่านั้นครับ",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    # ตั้งชื่อไฟล์
    display_name = name or image.filename
    file_ext = Path(image.filename).suffix
    safe_filename = f"{interaction.id}{file_ext}"
    file_path = IMAGES_DIR / safe_filename

    # ดาวน์โหลดและบันทึกไฟล์
    async with aiohttp.ClientSession() as session:
        async with session.get(image.url) as resp:
            if resp.status == 200:
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(await resp.read())

    # บันทึก index
    images = load_images()
    images.append({
        "name": display_name,
        "path": str(file_path),
        "uploaded_by": str(interaction.user),
        "filename": safe_filename
    })
    save_images(images)

    await interaction.followup.send(
        f"✅ เพิ่มรูปภาพ **{display_name}** เรียบร้อยแล้ว! (ทั้งหมด {len(images)} รูป)"
    )

# /list - ดูรายการรูปภาพทั้งหมด
@tree.command(name="list", description="ดูรายการรูปภาพทั้งหมดในคลัง")
async def list_images(interaction: discord.Interaction):
    images = load_images()

    if not images:
        await interaction.response.send_message(
            "📭 ยังไม่มีรูปภาพในคลังเลยครับ",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🖼️ คลังรูปภาพทั้งหมด",
        color=discord.Color.blue()
    )

    # แสดงสูงสุด 20 รูป
    display = images[:20]
    names = "\n".join([f"{i+1}. {img['name']}" for i, img in enumerate(display)])
    embed.description = names

    if len(images) > 20:
        embed.set_footer(text=f"แสดง 20/{len(images)} รูป")
    else:
        embed.set_footer(text=f"ทั้งหมด {len(images)} รูป")

    await interaction.response.send_message(embed=embed)

# /remove - ลบรูปภาพ
@tree.command(name="remove", description="ลบรูปภาพออกจากคลัง")
@app_commands.describe(name="ชื่อรูปภาพที่ต้องการลบ")
async def remove_image(interaction: discord.Interaction, name: str):
    images = load_images()
    found = next((img for img in images if img["name"].lower() == name.lower()), None)

    if not found:
        await interaction.response.send_message(
            f"❌ ไม่พบรูปภาพชื่อ **{name}** ครับ",
            ephemeral=True
        )
        return

    # ลบไฟล์
    file_path = Path(found["path"])
    if file_path.exists():
        file_path.unlink()

    images.remove(found)
    save_images(images)

    await interaction.response.send_message(
        f"🗑️ ลบรูปภาพ **{found['name']}** เรียบร้อยแล้วครับ"
    )

bot.run(TOKEN)
