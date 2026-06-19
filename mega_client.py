"""
MEGA API Client - Reverse Engineered
يُعمل بنفس طريقة MegaBasterd الأصلي (Java)
بدون حساب وبدون حزن 🎯
يدعم الملفات والمجلدات العامة
"""

import httpx
import json
import random
import string
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import logging
import asyncio
import base64

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 🔐 التشفير والحسابات (نفس طريقة Java)
# ============================================================================

class CryptoTools:
    """أدوات التشفير - نفس الخوارزميات اللي في Java"""
    
    @staticmethod
    def a32_to_str(a: List[int]) -> bytes:
        """تحويل مصفوفة 32-bit إلى bytes"""
        return b''.join(x.to_bytes(4, 'big') for x in a)
    
    @staticmethod
    def str_to_a32(s: bytes) -> List[int]:
        """تحويل bytes إلى مصفوفة 32-bit"""
        return [
            int.from_bytes(s[i:i+4], 'big') 
            for i in range(0, len(s), 4)
        ]
    
    @staticmethod
    def decrypt_key(encrypted_key: bytes, key: List[int]) -> bytes:
        """
        فك تشفير المفتاح - نفس طريقة Java
        ملاحظة: MEGA تستخدم AES-ECB للمفاتيح
        """
        from Crypto.Cipher import AES
        
        # تحويل المفتاح من مصفوفة 32-bit إلى bytes
        key_bytes = CryptoTools.a32_to_str(key)[:16]  # 128-bit key
        
        # فك تشفير بـ AES-ECB
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_key)
        
        return decrypted
    
    @staticmethod
    def aes_cbc_decrypt(
        ciphertext: bytes,
        key: bytes,
        iv: bytes
    ) -> bytes:
        """فك تشفير AES-CBC"""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted
    
    @staticmethod
    def aes_cbc_decrypt_no_pad(
        ciphertext: bytes,
        key: bytes,
        iv: bytes
    ) -> bytes:
        """فك تشفير AES-CBC بدون إزالة padding (للـ attributes)"""
        from Crypto.Cipher import AES
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(ciphertext)
    
    @staticmethod
    def base64_url_decode(s: str) -> bytes:
        """فك تشفير Base64 (MEGA style - no padding)"""
        # أضف padding إذا لزم الأمر
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += '=' * padding
        
        # استبدل الأحرف (MEGA يستخدم - و _ بدل + و /)
        s = s.replace('-', '+').replace('_', '/')
        
        try:
            return base64.b64decode(s)
        except Exception as e:
            logger.warning(f"Base64 decode error: {e}")
            return b''
    
    @staticmethod
    def base64_url_encode(data: bytes) -> str:
        """تشفير Base64 (MEGA style)"""
        encoded = base64.b64encode(data).decode('utf-8')
        # استبدل الأحرف
        encoded = encoded.replace('+', '-').replace('/', '_').rstrip('=')
        return encoded


# ============================================================================
# 📊 هياكل البيانات
# ============================================================================

@dataclass
class FileInfo:
    """معلومات الملف"""
    name: str
    size: int
    key: str
    type: str  # "file" أو "folder"
    node_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        size_str = self._format_size(self.size)
        icon = "📁" if self.type == "folder" else "📄"
        return f"{icon} {self.name:<50} {size_str:>15}"
    
    @staticmethod
    def _format_size(size: int) -> str:
        """تنسيق حجم الملف"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


@dataclass
class FolderContent:
    """محتويات المجلد"""
    files: List[FileInfo]
    folders: List[FileInfo]
    
    def __str__(self) -> str:
        result = []
        
        if self.folders:
            result.append("\n📁 المجلدات:")
            result.append("─" * 70)
            for folder in self.folders:
                result.append(str(folder))
        
        if self.files:
            result.append("\n📄 الملفات:")
            result.append("─" * 70)
            for file in self.files:
                result.append(str(file))
        
        return "\n".join(result)


# ============================================================================
# 🌐 عميل MEGA API
# ============================================================================

class MegaAPIClient:
    """عميل MEGA API - Reverse Engineered"""
    
    # الثوابت من Java
    API_URL = "https://g.api.mega.co.nz"
    DEFAULT_APP_KEY = "BdARkQSQ"  # من MEGAcmd الرسمي
    
    def __init__(self, timeout: int = 30):
        """تهيئة العميل"""
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None
        self.req_id = self._generate_req_id()
        self.seqno = 0
        
        logger.info("MEGA API Client initialized")
    
    @staticmethod
    def _generate_req_id(length: int = 10) -> str:
        """توليد req_id عشوائي (نفس Java)"""
        return ''.join(
            random.choices(string.ascii_letters + string.digits, k=length)
        )
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.aclose()
    
    async def _raw_request(self, request_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        إرسال طلب خام إلى API
        نفس الطريقة من Java MegaAPI.RAW_REQUEST()
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with'")
        
        # بناء الـ URL مع المعاملات
        params = {
            'id': self._next_seqno(),
            'ak': self.DEFAULT_APP_KEY,  # Application Key
        }
        
        url = f"{self.API_URL}/cs"
        
        try:
            # إرسال POST request
            response = await self.session.post(
                url,
                json=request_data,
                params=params,
                headers={
                    'User-Agent': 'MegaBasterd/8.57',
                    'Content-Type': 'application/json',
                }
            )
            
            response.raise_for_status()
            
            # معالجة الرد
            result = response.json()
            
            # التحقق من الأخطاء
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], int) and result[0] < 0:
                    error_code = result[0]
                    error_msg = self._get_error_message(error_code)
                    logger.error(f"MEGA API Error {error_code}: {error_msg}")
                    raise MegaAPIException(error_code, error_msg)
                
                return result[0] if result else {}
            
            return result
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            raise MegaNetworkException(str(e))
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}")
            raise MegaAPIException(-1, f"Invalid JSON response: {e}")
    
    def _next_seqno(self) -> str:
        """الحصول على رقم sequence التالي"""
        self.seqno += 1
        return str(self.seqno & 0xFFFFFFFF)
    
    @staticmethod
    def _get_error_message(code: int) -> str:
        """ترجمة رموز أخطاء MEGA"""
        error_codes = {
            -1: "EAGAIN - Generic error",
            -2: "EACCES - Access denied",
            -3: "EEXIST - Already exists",
            -4: "ENOENT - Does not exist",
            -5: "ECIRCULAR - Circular linkage",
            -6: "EACCES - Access violation",
            -9: "ENOENT - Nonsistent file or folder",
            -11: "EACCES - Identifier is not valid",
            -12: "ETOOMANY - Too many requests",
            -13: "ERANGE - Request out of range",
            -14: "EEXPIRED - Object (file/folder) has been deleted",
            -15: "ENOENT - Item not found",
            -16: "EBADTYPE - Permanent error",
            -17: "EOVERQUOTA - User has exceeded storage quota",
            -18: "ETEMPUNAVAIL - Resource temporarily unavailable",
            -19: "ETOOMANY - Too many requests for this resource",
            -20: "EKEY - Invalid or expired user session",
            -21: "ESID - User SID was reset",
            -22: "EBLOCKED - User blocked",
            -23: "EOVERQUOTA - Request over quota",
            -24: "EGOINGOVERQUOTA - Resource limit almost exceeded",
            -25: "EMFAREQUIRED - Multi-factor authentication required",
            -26: "EMASTERONLY - Access denied for sub-user",
            -27: "EBUS - Business account required",
            -28: "EPAYWALL - Over Disk Quota",
            -100: "EINTERNAL - Internal error",
        }
        return error_codes.get(code, f"Unknown error: {code}")
    
    async def get_folder_metadata(self, link: str) -> FolderContent:
        """
        الحصول على محتويات المجلد - نفس طريقة Java
        الرابط: https://mega.nz/folder/FOLDER_ID#KEY
        
        هذه الطريقة تجلب شجرة الملفات كاملة بدون حساب
        """
        folder_id, key_str = self._extract_file_info(link)
        
        if not folder_id or not key_str:
            raise ValueError("Invalid MEGA folder link format")
        
        logger.info(f"Fetching folder metadata for: {folder_id}")
        
        # فك تشفير المفتاح الأساسي
        key_bytes = CryptoTools.base64_url_decode(key_str)
        
        # الطلب: جلب شجرة الملفات بدون تسجيل دخول
        # نفس الطريقة من Java: MegaAPI.fetchNodes()
        request = [
            {
                "a": "f",  # fetch (جلب شجرة الملفات)
                "c": 1,    # اشمل الكل
            }
        ]
        
        try:
            response = await self._raw_request(request)
            
            # معالجة الرد وبناء شجرة الملفات
            files = []
            folders = []
            
            if isinstance(response, dict) and 'f' in response:
                # معالجة العقد
                for item in response['f']:
                    file_info = self._parse_folder_node(item, key_bytes)
                    if file_info:
                        if file_info.type == "folder":
                            folders.append(file_info)
                        else:
                            files.append(file_info)
            
            return FolderContent(files=files, folders=folders)
        
        except Exception as e:
            logger.error(f"Failed to get folder metadata: {e}")
            raise
    
    async def get_file_metadata(self, link: str) -> Tuple[str, int, str]:
        """
        الحصول على معلومات الملف من رابط عام
        يرجع: (اسم_الملف، الحجم، المفتاح)
        """
        file_id, key_str = self._extract_file_info(link)
        
        if not file_id or not key_str:
            raise ValueError("Invalid MEGA link format")
        
        logger.info(f"Fetching metadata for file: {file_id}")
        
        # بناء الطلب
        request = [
            {
                "a": "g",  # get file
                "p": file_id,
            }
        ]
        
        try:
            response = await self._raw_request(request)
            
            if isinstance(response, dict):
                size = response.get('s', 0)
                encrypted_attrs = response.get('at', '')
                
                file_name = self._decrypt_attributes(encrypted_attrs, key_str)
                
                return file_name or "Unknown", size, key_str
            
            raise MegaAPIException(-1, "Invalid response format")
        
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise
    
    @staticmethod
    def _extract_file_info(link: str) -> Tuple[Optional[str], Optional[str]]:
        """استخراج FILE_ID والمفتاح من رابط MEGA"""
        try:
            if '#' not in link:
                return None, None
            
            before_hash = link.split('#')[0]
            key = link.split('#')[1]
            
            parts = before_hash.rstrip('/').split('/')
            file_id = parts[-1]
            
            return file_id, key
        
        except Exception as e:
            logger.error(f"Failed to extract file info from link: {e}")
            return None, None
    
    @staticmethod
    def _decrypt_attributes(encrypted_attrs: str, key_str: str) -> Optional[str]:
        """فك تشفير الـ attributes للحصول على اسم الملف"""
        try:
            key_bytes = CryptoTools.base64_url_decode(key_str)
            
            if len(key_bytes) >= 32:
                file_key = key_bytes[16:32]
            else:
                file_key = key_bytes
            
            encrypted = CryptoTools.base64_url_decode(encrypted_attrs)
            
            iv = b'\x00' * 16
            decrypted = CryptoTools.aes_cbc_decrypt_no_pad(encrypted, file_key, iv)
            
            # إزالة padding يدويّاً
            padding_length = decrypted[-1] if decrypted else 0
            if 0 < padding_length <= 16:
                decrypted = decrypted[:-padding_length]
            
            attr_json = decrypted.decode('utf-8', errors='ignore')
            attr_dict = json.loads(attr_json)
            
            return attr_dict.get('n', 'Unknown')
        
        except Exception as e:
            logger.debug(f"Could not decrypt attributes: {e}")
            return None
    
    @staticmethod
    def _parse_folder_node(
        node: Dict[str, Any],
        parent_key: bytes
    ) -> Optional[FileInfo]:
        """تحليل عقدة ملف من المجلد"""
        try:
            node_type = node.get('t', 0)
            node_id = node.get('h')
            size = node.get('s', 0)
            encrypted_key = node.get('k', '')
            encrypted_attrs = node.get('a', '')
            
            if node_type not in [0, 1]:
                return None
            
            file_type = "folder" if node_type == 1 else "file"
            
            file_name = "Unknown"
            
            try:
                if encrypted_key and len(parent_key) > 0:
                    key_bytes = CryptoTools.base64_url_decode(encrypted_key)
                    actual_key = CryptoTools.decrypt_key(key_bytes, CryptoTools.str_to_a32(parent_key))
                    node_key = actual_key
                else:
                    node_key = parent_key
                
                if encrypted_attrs:
                    attr_bytes = CryptoTools.base64_url_decode(encrypted_attrs)
                    
                    if len(attr_bytes) > 8:
                        attr_data = attr_bytes[8:]
                    else:
                        attr_data = attr_bytes
                    
                    iv = b'\x00' * 16
                    try:
                        decrypted = CryptoTools.aes_cbc_decrypt_no_pad(attr_data, node_key[:16], iv)
                        
                        padding_length = decrypted[-1] if decrypted else 0
                        if 0 < padding_length <= 16:
                            decrypted = decrypted[:-padding_length]
                        
                        attr_json = decrypted.decode('utf-8', errors='ignore')
                        attr_dict = json.loads(attr_json)
                        file_name = attr_dict.get('n', file_name)
                    
                    except Exception as e:
                        logger.debug(f"Could not decrypt node attributes: {e}")
            
            except Exception as e:
                logger.debug(f"Error processing node key: {e}")
            
            return FileInfo(
                name=file_name,
                size=size,
                key=encrypted_key,
                type=file_type,
                node_id=node_id,
                attributes=node
            )
        
        except Exception as e:
            logger.debug(f"Failed to parse folder node: {e}")
            return None


# ============================================================================
# 🚨 الأخطاء المخصصة
# ============================================================================

class MegaException(Exception):
    """الخطأ الأساسي للـ MEGA"""
    pass


class MegaAPIException(MegaException):
    """خطأ في API MEGA"""
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MegaNetworkException(MegaException):
    """خطأ في الاتصال الشبكي"""
    pass
