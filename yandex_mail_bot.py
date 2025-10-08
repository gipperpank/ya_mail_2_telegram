import imaplib
import email
from email.header import decode_header
import telebot
from PIL import Image
import io
import os
import time
import threading
from datetime import datetime
import re
import sys
import html
from bs4 import BeautifulSoup

def check_dependencies():
    """Проверка установленных зависимостей"""
    try:
        import imapclient
        import telebot
        from PIL import Image
        import requests
        from bs4 import BeautifulSoup
        print("✓ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"✗ Отсутствует зависимость: {e}")
        print("Запустите create_venv_fixed.bat для установки зависимостей")
        return False

class YandexMailToTelegramBot:
    def __init__(self, email_config, telegram_config):
        self.email_config = email_config
        self.telegram_config = telegram_config
        self.bot = telebot.TeleBot(telegram_config['bot_token'])
        self.processed_emails = set()
        self.attachments_dir = "email_attachments"
        
        # Создаем папку для вложений
        if not os.path.exists(self.attachments_dir):
            os.makedirs(self.attachments_dir)
        
    def connect_to_email(self):
        """Подключение к Яндекс.Почте"""
        try:
            print("Подключение к Яндекс.Почте...")
            self.mail = imaplib.IMAP4_SSL("imap.yandex.ru", 993)
            self.mail.login(self.email_config['email'], self.email_config['password'])
            self.mail.select("INBOX")
            print("✓ Успешно подключено к Яндекс.Почте")
            return True
        except Exception as e:
            print(f"✗ Ошибка подключения к почте: {e}")
            return False
    
    def mark_as_read(self, email_id):
        """Помечает письмо как прочитанное"""
        try:
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            print(f"✓ Письмо {email_id} помечено как прочитанное")
            return True
        except Exception as e:
            print(f"✗ Ошибка пометки письма как прочитанного: {e}")
            return False
    
    def decode_mime_words(self, text):
        """Декодирование заголовков писем"""
        try:
            if text is None:
                return "Без темы"
            decoded_parts = decode_header(text)
            decoded_text = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_text += part.decode(encoding)
                    else:
                        decoded_text += part.decode('utf-8', errors='ignore')
                else:
                    decoded_text += part
            return decoded_text
        except:
            return str(text) if text else "Без темы"
    
    def clean_html_to_text(self, html_content):
        """Тщательная очистка HTML от мусора и преобразование в читаемый текст"""
        if not html_content:
            return ""
        
        try:
            # Используем BeautifulSoup для парсинга HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Удаляем ненужные элементы
            for element in soup(['script', 'style', 'meta', 'link', 'head', 'title']):
                element.decompose()
            
            # Удаляем элементы с определенными классами или ID (типичный мусор в письмах)
            garbage_selectors = [
                '[class*="hidden"]', '[class*="hide"]', '.footer', '.header',
                '[class*="banner"]', '[class*="ad"]', '.signature', '.disclaimer',
                '.copyright', '.logo', '.social', '.share', '.button', '.btn',
                '[style*="display:none"]', '[style*="display: none"]',
                '.email-footer', '.email-header', '.mailing', '.campaign'
            ]
            
            for selector in garbage_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Получаем чистый текст
            text = soup.get_text()
            
            # Очищаем текст от лишних пробелов и переносов
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if line:  # убираем пустые строки
                    lines.append(line)
            
            clean_text = '\n'.join(lines)
            
            # Убираем множественные пробелы
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # Убираем мусорные паттерны, часто встречающиеся в email рассылках
            garbage_patterns = [
                r'\[.*?\]',  # текст в квадратных скобках
                r'&nbsp;',   # HTML неразрывные пробелы
                r'<!--.*?-->',  # HTML комментарии
                r'https?://\S+',  # ссылки (оставляем только текст)
            ]
            
            for pattern in garbage_patterns:
                clean_text = re.sub(pattern, ' ', clean_text)
            
            # Декодируем HTML entities
            clean_text = html.unescape(clean_text)
            
            # Финальная очистка
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            return clean_text
            
        except Exception as e:
            print(f"Ошибка очистки HTML: {e}")
            # Если BeautifulSoup не справился, используем базовый метод
            return self.basic_html_clean(html_content)
    
    def basic_html_clean(self, html_content):
        """Базовый метод очистки HTML без BeautifulSoup"""
        if not html_content:
            return ""
        
        # Удаляем HTML теги
        text = re.sub('<[^<]+?>', ' ', html_content)
        
        # Удаляем HTML комментарии
        text = re.sub('<!--.*?-->', ' ', text)
        
        # Заменяем HTML сущности
        text = html.unescape(text)
        
        # Убираем мусорные паттерны
        text = re.sub(r'\[.*?\]', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        
        # Убираем лишние пробелы и переносы
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line and len(line) > 2:  # убираем очень короткие строки (часто мусор)
                lines.append(line)
        
        clean_text = '\n'.join(lines)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def extract_text_from_email(self, msg):
        """Извлечение текста из письма"""
        text_content = ""
        html_content = ""
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # Пропускаем вложения
                    if 'attachment' in content_disposition:
                        continue
                        
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                decoded_text = payload.decode('utf-8', errors='ignore')
                                text_content += decoded_text
                        except:
                            pass
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                decoded_html = payload.decode('utf-8', errors='ignore')
                                html_content += decoded_html
                        except:
                            pass
            else:
                content_type = msg.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            text_content = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html":
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
            
            # Предпочитаем чистый текст, если он есть
            if text_content.strip():
                clean_text = text_content
            elif html_content.strip():
                # Очищаем HTML от мусора
                print("Обнаружен HTML контент, выполняется очистка...")
                clean_text = self.clean_html_to_text(html_content)
                print("HTML очищен успешно")
            else:
                clean_text = "Текст письма отсутствует или не может быть прочитан"
            
            return clean_text
            
        except Exception as e:
            print(f"Ошибка извлечения текста: {e}")
            return "Ошибка при чтении содержимого письма"
    
    def extract_attachments(self, msg):
        """Извлечение всех вложений из письма"""
        images = []
        files = []
        
        try:
            print("Начало извлечения вложений...")
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    filename = part.get_filename()
                    
                    # Если есть имя файла, это вложение
                    if filename:
                        filename = self.decode_mime_words(filename)
                        print(f"Обнаружено вложение: {filename} ({content_type})")
                        
                        # Декодируем содержимое вложения
                        try:
                            file_data = part.get_payload(decode=True)
                            if file_data:
                                file_info = {
                                    'filename': filename,
                                    'data': file_data,
                                    'type': content_type,
                                    'size': len(file_data)
                                }
                                
                                print(f"Вложение {filename} успешно извлечено, размер: {len(file_data)} байт")
                                
                                # Разделяем на изображения и другие файлы
                                if content_type.startswith("image/"):
                                    images.append(file_info)
                                    print(f"Добавлено изображение: {filename}")
                                else:
                                    files.append(file_info)
                                    print(f"Добавлен файл: {filename}")
                            else:
                                print(f"Пустые данные для вложения: {filename}")
                                
                        except Exception as e:
                            print(f"Ошибка декодирования вложения {filename}: {e}")
            
            print(f"Итог: изображений - {len(images)}, файлов - {len(files)}")
            return images, files
            
        except Exception as e:
            print(f"Ошибка при извлечении вложений: {e}")
            return [], []
    
    def save_attachment(self, file_data, filename):
        """Сохраняет вложение в папку и возвращает путь"""
        try:
            # Очищаем имя файла от недопустимых символов
            clean_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join(self.attachments_dir, clean_filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            print(f"Файл сохранен: {filepath}")
            return filepath
        except Exception as e:
            print(f"Ошибка сохранения файла {filename}: {e}")
            return None
    
    def format_file_size(self, size_bytes):
        """Форматирует размер файла в читаемый вид"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def format_email_message(self, msg, files):
        """Форматирование письма для отправки в Telegram"""
        try:
            subject = self.decode_mime_words(msg.get("Subject", "Без темы"))
            from_ = self.decode_mime_words(msg.get("From", "Неизвестный отправитель"))
            date = msg.get("Date", "Неизвестная дата")
            
            text_content = self.extract_text_from_email(msg)
            
            # Обрезаем длинный текст
            if len(text_content) > 1500:
                text_content = text_content[:1500] + "...\n\n[Текст обрезан]"
            
            message = f"📧 *Новое письмо*\n\n"
            message += f"🤵 *От:* {from_}\n"
            message += f"📣 *Тема:* {subject}\n"
            message += f"📆 *Дата:* {date}\n"
            
            # Добавляем информацию о вложениях
            if files:
                message += f"💾 \n*Вложения ({len(files)}):*\n"
                for i, file_info in enumerate(files, 1):
                    file_size = self.format_file_size(file_info['size'])
                    message += f"💾 {i}. {file_info['filename']} ({file_size})\n"
            
            message += f"\n*Содержимое:*\n{text_content}"
            
            return message
        except Exception as e:
            print(f"Ошибка форматирования письма: {e}")
            base_message = "📧 *Новое письмо*\n\n"
            base_message += f"🤵 *От:* {msg.get('From', 'Неизвестный отправитель')}\n"
            base_message += f"📣 *Тема:* {msg.get('Subject', 'Без темы')}\n"
            base_message += "\nНе удалось полностью прочитать содержимое письма"
            return base_message
    
    def send_to_telegram(self, email_message, images, files, email_id):
        """Отправка письма, изображений и информации о файлах в Telegram"""
        success = False
        try:
            chat_id = self.telegram_config['chat_id']
            
            print("Начало отправки в Telegram...")
            
            # Сначала отправляем текст письма
            try:
                self.bot.send_message(chat_id, email_message, parse_mode='Markdown')
                print("✓ Текст письма отправлен")
                success = True
            except Exception as e:
                print(f"✗ Ошибка отправки текста: {e}")
                return False
            
            # Затем отправляем изображения (если есть)
            if images:
                print(f"Отправка {len(images)} изображений...")
                
                try:
                    # Для изображений используем медиагруппу если их несколько
                    if len(images) > 1:
                        media_group = []
                        for img in images:
                            photo = io.BytesIO(img['data'])
                            photo.name = img['filename']
                            media_group.append(telebot.types.InputMediaPhoto(photo))
                        
                        self.bot.send_media_group(chat_id, media_group)
                        print(f"✓ Отправлено {len(images)} изображений медиагруппой")
                    else:
                        # Одно изображение
                        img = images[0]
                        photo = io.BytesIO(img['data'])
                        photo.name = img['filename']
                        self.bot.send_photo(chat_id, photo)
                        print(f"✓ Изображение отправлено")
                        
                except Exception as e:
                    print(f"Ошибка отправки изображений: {e}")
                    # Продолжаем обработку даже если изображения не отправились
            
            # Обрабатываем файлы (не изображения)
            if files:
                print(f"Отправка {len(files)} файлов...")
                
                for i, file_info in enumerate(files, 1):
                    try:
                        print(f"Отправка файла {i}/{len(files)}: {file_info['filename']}")
                        
                        # Для файлов используем send_document
                        file_io = io.BytesIO(file_info['data'])
                        file_io.name = file_info['filename']
                        
                        self.bot.send_document(
                            chat_id, 
                            file_io, 
                            visible_file_name=file_info['filename'],
                            caption=f"Файл из письма: {file_info['filename']}"
                        )
                        print(f"✓ Файл {file_info['filename']} отправлен")
                        
                        # Небольшая пауза между отправкой файлов
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Ошибка отправки файла {file_info['filename']}: {e}")
            
            print("✓ Все данные отправлены в Telegram")
            return True
            
        except Exception as e:
            print(f"✗ Критическая ошибка отправки в Telegram: {e}")
            return False
    
    def process_new_emails(self):
        """Обработка новых писем"""
        mail_connection = None
        try:
            if not self.connect_to_email():
                return False
            
            mail_connection = self.mail
            
            # Поиск непрочитанных писем
            print("Поиск непрочитанных писем...")
            status, messages = mail_connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                print("✗ Ошибка поиска писем")
                return False
            
            email_ids = messages[0].split()
            
            if not email_ids:
                print("✓ Новых писем нет")
                return True
            
            print(f"Найдено {len(email_ids)} новых писем")
            
            for email_id in email_ids:
                email_id_str = email_id.decode('utf-8')
                
                if email_id_str in self.processed_emails:
                    print(f"Письмо {email_id_str} уже обработано, пропускаем")
                    continue
                
                print(f"Обработка письма ID: {email_id_str}")
                
                status, msg_data = mail_connection.fetch(email_id, '(RFC822)')
                
                if status != 'OK':
                    print(f"✗ Ошибка получения письма {email_id_str}")
                    continue
                
                if not msg_data or not msg_data[0]:
                    print(f"✗ Пустые данные письма {email_id_str}")
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                from_header = msg.get('From', 'Неизвестный отправитель')
                subject_header = msg.get('Subject', 'Без темы')
                print(f"Письмо от: {from_header}")
                print(f"Тема: {subject_header}")
                
                # Извлекаем вложения
                images, files = self.extract_attachments(msg)
                
                if images:
                    print(f" - Найдено изображений: {len(images)}")
                if files:
                    print(f" - Найдено файлов: {len(files)}")
                
                email_message = self.format_email_message(msg, files)
                
                # Отправка в Telegram
                if self.send_to_telegram(email_message, images, files, email_id_str):
                    # Помечаем письмо как прочитанное только если отправка успешна
                    self.mark_as_read(email_id)
                    self.processed_emails.add(email_id_str)
                    print("✓ Письмо успешно обработано и помечено как прочитанное")
                else:
                    print("✗ Не удалось отправить письмо в Telegram, оставляем непрочитанным")
                
                # Пауза между отправками
                print("Пауза 3 секунды перед следующим письмом...")
                time.sleep(3)
            
            mail_connection.close()
            mail_connection.logout()
            return True
            
        except Exception as e:
            print(f"✗ Ошибка обработки писем: {e}")
            if mail_connection:
                try:
                    mail_connection.close()
                    mail_connection.logout()
                except:
                    pass
            return False
    
    def start_monitoring(self, interval=60):
        """Запуск мониторинга почты"""
        print(f"🚀 Запуск мониторинга почты")
        print(f"📧 Email: {self.email_config['email']}")
        print(f"⏱  Интервал проверки: {interval} секунд")
        print(f"💬 Telegram чат: {self.telegram_config['chat_id']}")
        print(f"📁 Папка для вложений: {self.attachments_dir}")
        print("-" * 50)
        
        def monitor():
            while True:
                try:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка почты...")
                    self.process_new_emails()
                    time.sleep(interval)
                except Exception as e:
                    print(f"Ошибка в мониторинге: {e}")
                    time.sleep(interval)
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print("Мониторинг запущен. Для остановки нажмите Ctrl+C\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nМониторинг остановлен пользователем")

def main():
    print("Yandex Mail to Telegram Bot")
    print("=" * 30)
    
    # Проверка зависимостей
    if not check_dependencies():
        print("Пожалуйста, установите зависимости и запустите снова")
        return
    
    # Конфигурация - ЗАМЕНИТЕ НА СВОИ ДАННЫЕ!
    email_config = {
        'email': 'почта@yandex.ru',  # ЗАМЕНИТЕ
        'password': 'пароль почты'    # ЗАМЕНИТЕ (пароль приложения)
    }
    
    telegram_config = {
        'bot_token': 'бот токен',     # ЗАМЕНИТЕ
        'chat_id': 'ваш чат ID '          # ЗАМЕНИТЕ
    }
    
    # Проверка заполнения конфигурации
    if (email_config['email'] == 'your_email@yandex.ru' or 
        telegram_config['bot_token'] == 'your_bot_token'):
        print("\n❌ ОШИБКА: Не настроена конфигурация!")
        print("Пожалуйста, откройте файл yandex_mail_bot.py")
        print("и замените значения в секции конфигурации на свои данные:")
        print("- Яндекс email и пароль приложения")
        print("- Токен Telegram бота")
        print("- ID Telegram чата")
        input("Нажмите Enter для выхода...")
        return
    
    # Создание и запуск бота
    try:
        mail_bot = YandexMailToTelegramBot(email_config, telegram_config)
        mail_bot.start_monitoring(interval=60)  # Проверка каждые 60 секунд
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()