# ห้อง Minecraft พร้อมเคส RGB

เปิด `satou-monitor-room.blend` ใน Blender 5.3 ขึ้นไป แล้วกด F12 ฉากตั้ง Cycles / GPU Compute และ GPU denoising ไว้แล้ว เลือก RTX ใน Preferences > System > OptiX ด้วย

## สิ่งที่เพิ่ม

- เคสกระจก RTX 5070 อยู่หลังจอวางพื้นสองจอ ตามกรอบสีเขียวในภาพอ้างอิง: RAM RGB 4 แถว, พัดลม 3 ตัว, CPU ชุดน้ำ, สายไฟแยกเส้น 18 เส้น และ cable comb
- จอวางพื้นสองจอต่อกันที่ขอบและหักมุม ตามกรอบสีแดงในภาพอ้างอิง อยู่ด้านซ้ายหน้าน้องเล่นมือถือ
- หกจอหลักใช้ screenshot จากเกมในเครื่องคนละภาพ จอวางพื้นสองจอใช้ภาพที่เจ็ดและแปด รวมจอภาพในห้อง 10 จอ
- จอขวาใช้ภาพโค้ดสองหน้า วาดจาก `monitor_room.py` พร้อม syntax highlighting
- ชั้นหนังสือเป็นแผ่นไม้บนผนังอิฐ มีขารับเหล็ก หนังสือหลายขนาด สีสัน และหนังสือที่วางซ้อนตามภาพตัวอย่าง
- ตัวละครในห้องนำเข้าใหม่จาก `pink_bun_winefox_square_eyes` และ `pink_bun_winefox_white_square_eyes`
- โฟลเดอร์ `library/` มีโมเดลใหม่ครบทั้งห้าแบบ และ `satou-all-characters.blend` สำหรับดูรวมกัน

## กล้อง

เลือกกล้องผ่าน Outliner แล้วตั้งเป็น Active Camera: `01 - Reference composition`, `02 - Low seated character`, `03 - Desk and screen arrangement`, `04 - Panoramic RGB computer`, `05 - Left room overview`, `06 - Reverse room and characters`, `07 - RTX 5070 computer side`, `08 - Seated phone side view`

ภาพห้องทั้งแปดมุมเรนเดอร์ 2560 × 1440, Cycles / OptiX, สูงสุด 192 samples ภาพรวมตัวละคร 2560 × 1080

มุม 06 หันเข้าหาด้านที่รับแสงจอโดยตรง สคริปต์ลด Exposure ลง 1.8 stops เฉพาะภาพนี้ หากเลือกกล้องนี้แล้วกด F12 เอง ให้ตั้ง Color Management > Exposure เป็น -1.7 ส่วนกล้องอื่นใช้ 0.1

## โพสนั่งและมือถือ

โพส `scene_floor_phone` ตั้งตำแหน่งต้นขาที่รองรับตัวให้อยู่ห่างพื้น 0.002 หน่วยฉาก แล้วแก้มุมเข่าให้เท้าสัมผัสพื้นในระดับเดียวกัน ตรวจจาก vertex ของทั้งต้นขาและเท้าแยกกัน มือถือเป็น mesh เดียว มีพื้นผิวจอหนึ่งด้าน ส่วนจอสองจอในกรอบแดงเป็นจอวางพื้นที่ต่อกัน โดยมีเคสในกรอบเขียวอยู่ด้านหลัง จอทั้งสองมีฐานรองแยกจากมือถือ

## แก้เคสและไฟ

ทุกชิ้นขึ้นต้นชื่อ `PC -` และอยู่ใต้ Empty `PC - Aurora panoramic tower` ย้าย/หมุน Empty นี้เพื่อจัดตำแหน่งทั้งเคส ชิ้นส่วน RAM, fan ring, braided power lead และกระจกเป็น geometry แยกชิ้น วัสดุ `PC - RGB 0` ถึง `PC - RGB 11` กำหนดสีและ Emission Strength

จอวางพื้นอยู่ใต้ Empty `Low floor display left` และ `Low floor display right` ตำแหน่งรอยต่ออยู่ใกล้กันแต่หักมุมต่างกัน เคสย่อสัดส่วนและวางด้านหลังชุดจอตามภาพ โค้ดชั้นหนังสืออยู่ใน `bookshelves.py` มีแผ่นไม้ฝั่งละ 6 ระดับ ผนังอิฐ และไฟใต้ชั้นอ่อน ๆ วัสดุไฟชื่อ `Library - subtle warm shelf strip` ปรับ Emission Strength เพื่อเปลี่ยนความสว่างได้

## เปลี่ยนภาพบนจอ

เลือกวัตถุ `... Minecraft screen` เปิด Shader Editor และเปลี่ยนภาพที่ Image Texture ชื่อ `Minecraft screenshot` แล้วเรนเดอร์ใหม่ สีในภาพส่งเข้า Emission จึงเปลี่ยนสีแสงในห้องได้ด้วย จอหลักตั้ง Emission Strength 120, จอโค้ด 45 และ shader ที่กล้องเห็นตั้ง 0.8 เพื่อให้ภาพไม่ขาวล้น ค่าเหล่านี้ใช้จัดแสงภาพ ไม่ใช่หน่วย nit ของจอจริง

ทุกจอมี material แยกกัน ภาพแพ็กในไฟล์แล้ว เมื่อเลือกภาพใหม่ที่สัดส่วนต่างกัน อาจต้องปรับ UV ให้เหมาะสม

## โมเดลและ actions

ไฟล์โมเดลแต่ละตัวมี root Empty, armature, mesh, packed pixel texture และ actions ที่ใช้ตรวจงาน ตัวละคร Satou สี่แบบมี 47 review actions ต่อคน คุณน้ามี 33 review actions ที่มีอยู่จริงใน source ของคุณน้า จึงไม่มี action หน้าตาแปดแบบหรือบาง action ของน้อง ชื่อ action ที่นำเข้าอยู่ใน `library/manifest.json` อนิเมชันจากม็อดอาวุธหรือ controller เฉพาะเกมไม่ได้รวมเป็น review actions

ฉากห้องมี 95 actions: 47 ต่อคน และโพสนั่งอ่านโทรศัพท์อีกหนึ่ง action ไฟล์รวมตัวละครมี 221 review actions

ใช้ File > Append > เลือกไฟล์ใน library > Collection เพื่อนำตัวอื่นเข้าไฟล์งาน เมื่อนำเข้าใหม่ให้เปิด fake user ของ actions ที่ต้องเก็บก่อนบันทึก

## สร้างซ้ำจาก repository

โค้ดสำเนาอยู่ใน `source/` ให้วางกลับที่ `renderer/blender/` ใน repository ก่อนรัน คำสั่งทำจาก root ของ repository และต้องมี Python/Pillow กับ Blender ใน PATH

```powershell
npm test
python renderer/blender/import_all_characters.py --prepare
blender -b --python-exit-code 1 --python renderer/blender/import_all_characters.py
python renderer/blender/prepare_monitor_screens.py
blender -b --python-exit-code 1 --python renderer/blender/monitor_room.py -- --all --output output/blender-scenes/monitor-room-rgb
blender -b --python-exit-code 1 --python renderer/blender/check_monitor_room_rgb.py
```

`prepare_monitor_screens.py` ใช้ชื่อ screenshot ของผู้ใช้ตามวันที่ในโค้ด เปลี่ยนรายการ `SELECTED` และ `CAPTURES` เมื่อต้องใช้ภาพชุดอื่น

## การตรวจและเครดิต

ตรวจ source SHA-256 ของทั้งห้าโมเดล, เปรียบเทียบ mesh Blender กับตัวอ่าน YSM ที่หลายโพส, เปิดไฟล์กลับมาตรวจ 6 ภาพหลักไม่ซ้ำกันและภาพจอทั้ง 10 จอไม่ซ้ำ, รอยต่อจอวางพื้นสองจอ, เคสอยู่ด้านหลังจอ, packed textures, RAM และสายไฟ ผลอยู่ใน `validation.json` และ `library/*.validation.json` การตรวจนี้เป็นการเทียบตัวเลขกับการดูภาพเรนเดอร์ ไม่ใช่ทดสอบอนิเมชันทั้งหมดใน Minecraft

ภาพเกมเป็น screenshot จากเครื่องผู้ใช้ Minecraft เป็นของ Mojang/Microsoft เครดิต Wine Fox และ CC BY-NC-SA 4.0 อยู่ใน `CHARACTER-ATTRIBUTION.md` และ Text blocks ของแต่ละโมเดล
