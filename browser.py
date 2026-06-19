"""
MEGA File Browser - متصفح ملفات MEGA بدون حساب
عرض الملفات والمجلدات والأحجام بشكل تفاعلي
"""

import asyncio
import sys
from typing import Optional
from mega_client import (
    MegaAPIClient,
    FileInfo,
    FolderContent,
    MegaAPIException,
    MegaNetworkException,
    CryptoTools
)
import logging
from pathlib import Path
import json

logging.basicConfig(
    level=logging.WARNING,  # قلل المشاكل
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MegaBrowser:
    """متصفح MEGA التفاعلي"""
    
    def __init__(self):
        self.current_path = []
        self.current_items = []
        self.last_result = None
    
    def print_header(self):
        """طباعة رأس البرنامج"""
        print("\n" + "=" * 80)
        print("🎯 MEGA FILE BROWSER - متصفح ملفات ميقا بدون حساب".center(80))
        print("=" * 80)
        print("⚡ طريقة العمل:")
        print("   1️⃣  أدخل رابط ملف أو مجلد من MEGA")
        print("   2️⃣  سيتم عرض محتوياته بدون الحاجة لتسجيل دخول")
        print("   3️⃣  شاهد أسماء الملفات والمجلدات والأحجام")
        print("=" * 80 + "\n")
    
    @staticmethod
    def format_size(size: int) -> str:
        """تنسيق حجم الملف بشكل جميل"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size < 1024:
                if unit == 'B':
                    return f"{size:,.0f} {unit}"
                return f"{size:,.2f} {unit}"
            size /= 1024
        return f"{size:,.2f} EB"
    
    async def fetch_file_info(self, link: str) -> Optional[dict]:
        """جلب معلومات الملف"""
        print(f"\n⏳ جاري جلب معلومات الملف...")
        
        try:
            async with MegaAPIClient(timeout=15) as client:
                # استخراج معلومات الملف من الرابط
                file_id, key = client._extract_file_info(link)
                
                if not file_id or not key:
                    print("❌ صيغة الرابط غير صحيحة!")
                    print("   الصيغة الصحيحة: https://mega.nz/file/FILE_ID#KEY")
                    return None
                
                print(f"📄 معرّف الملف: {file_id}")
                print(f"🔑 المفتاح: {key[:20]}...")
                
                try:
                    # محاولة جلب البيانات الوصفية
                    name, size, _ = await client.get_file_metadata(link)
                    
                    result = {
                        'type': 'file',
                        'name': name,
                        'size': size,
                        'file_id': file_id,
                        'key': key,
                        'link': link
                    }
                    
                    return result
                
                except MegaAPIException as e:
                    if e.code == -9:
                        print("❌ الملف غير موجود أو تم حذفه")
                    elif e.code == -16:
                        print("❌ الملف محذوف أو مقيد")
                    else:
                        print(f"⚠️  خطأ في API: {e}")
                    
                    # رغم الخطأ، نرجع معلومات أساسية
                    return {
                        'type': 'file',
                        'name': 'Unknown File',
                        'size': 0,
                        'file_id': file_id,
                        'key': key,
                        'link': link,
                        'error': str(e)
                    }
        
        except MegaNetworkException as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return None
        
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}")
            return None
    
    async def fetch_folder_info(self, link: str) -> Optional[dict]:
        """جلب معلومات المجلد"""
        print(f"\n⏳ جاري جلب محتويات المجلد...")
        
        try:
            async with MegaAPIClient(timeout=15) as client:
                # استخراج معرّف المجلد والمفتاح
                folder_id, key = client._extract_file_info(link)
                
                if not folder_id or not key:
                    print("❌ صيغة الرابط غير صحيحة!")
                    print("   الصيغة الصحيحة: https://mega.nz/folder/FOLDER_ID#KEY")
                    return None
                
                print(f"📁 معرّف المجلد: {folder_id}")
                print(f"🔑 المفتاح: {key[:20]}...")
                
                try:
                    # جلب محتويات المجلد
                    content = await client.get_folder_metadata(link)
                    
                    result = {
                        'type': 'folder',
                        'folder_id': folder_id,
                        'key': key,
                        'link': link,
                        'files': content.files,
                        'folders': content.folders,
                    }
                    
                    return result
                
                except MegaAPIException as e:
                    print(f"⚠️  لم يتمكن من جلب المحتويات: {e}")
                    
                    return {
                        'type': 'folder',
                        'folder_id': folder_id,
                        'key': key,
                        'link': link,
                        'files': [],
                        'folders': [],
                        'error': str(e)
                    }
        
        except MegaNetworkException as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return None
        
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}")
            return None
    
    def display_file_info(self, info: dict):
        """عرض معلومات الملف"""
        print("\n" + "─" * 80)
        print("📄 معلومات الملف:")
        print("─" * 80)
        
        print(f"📝 الاسم: {info['name']}")
        print(f"💾 الحجم: {self.format_size(info['size'])}")
        print(f"🔗 الرابط: {info['link']}")
        print(f"📛 المعرّف: {info['file_id']}")
        print(f"🔐 المفتاح: {info['key']}")
        
        if 'error' in info:
            print(f"⚠️  ملاحظة: {info['error']}")
        
        print("─" * 80)
    
    def display_folder_info(self, info: dict):
        """عرض معلومات المجلد"""
        print("\n" + "─" * 80)
        print("📁 معلومات المجلد:")
        print("─" * 80)
        
        print(f"🔗 الرابط: {info['link']}")
        print(f"📛 المعرّف: {info['folder_id']}")
        print(f"🔐 المفتاح: {info['key']}")
        
        folders = info.get('folders', [])
        files = info.get('files', [])
        
        print(f"\n📊 الإحصائيات:")
        print(f"   📁 عدد المجلدات: {len(folders)}")
        print(f"   📄 عدد الملفات: {len(files)}")
        
        total_size = sum(f.size for f in files)
        print(f"   💾 الحجم الكلي: {self.format_size(total_size)}")
        
        # عرض المجلدات
        if folders:
            print(f"\n📁 المجلدات ({len(folders)}):")
            print("─" * 80)
            print(f"{'الاسم':<50} {'الحجم':>15} {'النوع':>10}")
            print("─" * 80)
            
            for folder in folders:
                print(f"{folder.name:<50} {self.format_size(folder.size):>15} {'📁':>10}")
        
        # عرض الملفات
        if files:
            print(f"\n📄 الملفات ({len(files)}):")
            print("─" * 80)
            print(f"{'الاسم':<50} {'الحجم':>15} {'النوع':>10}")
            print("─" * 80)
            
            for file in files:
                print(f"{file.name:<50} {self.format_size(file.size):>15} {'📄':>10}")
        
        if 'error' in info:
            print(f"\n⚠️  ملاحظة: {info['error']}")
        
        print("─" * 80)
    
    async def process_link(self, link: str):
        """معالجة رابط MEGA"""
        link = link.strip()
        
        if not link.startswith(('http://', 'https://')):
            print("❌ الرابط يجب أن يبدأ بـ http أو https")
            return
        
        # تحديد نوع الرابط
        if '/folder/' in link or 'mega.nz/folder' in link or 'mega.co.nz/folder' in link:
            info = await self.fetch_folder_info(link)
            if info:
                self.last_result = info
                self.display_folder_info(info)
        
        elif '/file/' in link or 'mega.nz/file' in link or 'mega.co.nz/file' in link:
            info = await self.fetch_file_info(link)
            if info:
                self.last_result = info
                self.display_file_info(info)
        
        else:
            print("❌ نوع الرابط غير مدعوم")
            print("   الروابط المدعومة:")
            print("   • ملفات: https://mega.nz/file/FILE_ID#KEY")
            print("   • مجلدات: https://mega.nz/folder/FOLDER_ID#KEY")
    
    def save_result(self, filename: str = "mega_result.json"):
        """حفظ النتيجة في ملف JSON"""
        if not self.last_result:
            print("❌ لا توجد نتائج لحفظها")
            return
        
        try:
            # تحويل الكائنات إلى قاموس
            data = self._serialize_result(self.last_result)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ تم حفظ النتائج في: {filename}")
        
        except Exception as e:
            print(f"❌ خطأ في الحفظ: {e}")
    
    @staticmethod
    def _serialize_result(result: dict) -> dict:
        """تحويل النتيجة إلى قاموس قابل للتسلسل"""
        if result.get('type') == 'file':
            return {
                'type': 'file',
                'name': result.get('name'),
                'size': result.get('size'),
                'file_id': result.get('file_id'),
                'key': result.get('key'),
                'link': result.get('link'),
            }
        
        else:  # folder
            files = []
            for f in result.get('files', []):
                files.append({
                    'name': f.name,
                    'size': f.size,
                    'type': 'file'
                })
            
            folders = []
            for folder in result.get('folders', []):
                folders.append({
                    'name': folder.name,
                    'size': folder.size,
                    'type': 'folder'
                })
            
            return {
                'type': 'folder',
                'folder_id': result.get('folder_id'),
                'key': result.get('key'),
                'link': result.get('link'),
                'files': files,
                'folders': folders,
            }
    
    def show_help(self):
        """عرض المساعدة"""
        print("\n" + "=" * 80)
        print("📚 الأوامر المتاحة:")
        print("=" * 80)
        print("""
1️⃣  أدخل رابط MEGA:
    • للملفات: https://mega.nz/file/FILE_ID#KEY
    • للمجلدات: https://mega.nz/folder/FOLDER_ID#KEY

2️⃣  أوامر خاصة:
    • help     → عرض هذه الرسالة
    • save     → حفظ آخر نتيجة في ملف JSON
    • clear    → مسح الشاشة
    • exit     → الخروج من البرنامج

3️⃣  المميزات:
    ✅ لا تحتاج حساب MEGA
    ✅ عرض الملفات والمجلدات
    ✅ عرض الأحجام الحقيقية
    ✅ دعم الروابط المشفرة
    ✅ حفظ النتائج في JSON
        """)
        print("=" * 80)


async def main():
    """البرنامج الرئيسي"""
    browser = MegaBrowser()
    browser.print_header()
    
    print("💡 أكتب 'help' لعرض الأوامر المتاحة\n")
    
    try:
        while True:
            try:
                user_input = input("🔗 أدخل رابط MEGA أو أمر (help/save/exit): ").strip()
                
                if not user_input:
                    continue
                
                # معالجة الأوامر الخاصة
                if user_input.lower() == 'exit':
                    print("👋 شكراً لاستخدام MEGA Browser!")
                    break
                
                elif user_input.lower() == 'help':
                    browser.show_help()
                
                elif user_input.lower() == 'save':
                    filename = input("📁 أدخل اسم الملف (أو اترك فارغاً للافتراضي): ").strip()
                    if not filename:
                        filename = "mega_result.json"
                    browser.save_result(filename)
                
                elif user_input.lower() == 'clear':
                    import os
                    os.system('cls' if sys.platform == 'win32' else 'clear')
                    browser.print_header()
                
                else:
                    # معالجة الرابط
                    await browser.process_link(user_input)
            
            except KeyboardInterrupt:
                print("\n\n👋 تم الإيقاف من قبل المستخدم")
                break
            
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                print(f"❌ خطأ: {e}")
    
    except Exception as e:
        print(f"❌ خطأ حرج: {e}")
        logger.error(f"Critical error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
