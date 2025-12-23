# TTS-Grabber
Quick thing i made about a year ago to download any text with any tts voice, 829 voices to choose from currently.

The program will split the input into multiple files every 1500 words or so to not hit any cutoff limits from TTS providers.

## Cài đặt (Installation)

```bash
pip install requests
```

Để sử dụng phiên bản GUI, cần cài đặt thêm:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS (thường đã được cài sẵn)
# Windows (thường đã được cài sẵn)
```

## Usage:  
Edit `input.txt` to change the text to synthesize.

You can run just `tts.py` without any parameters to open the voice selector with default settings.  

### Giao diện đồ họa (GUI Version)

Chạy ứng dụng GUI với:
```bash
python tts_gui.py
```

**Tính năng của GUI:**
- 📝 Nhập văn bản trực tiếp hoặc mở file .txt
- 🎬 Import file SRT để tạo voice cho từng đoạn phụ đề
- 🔍 Tìm kiếm và lọc giọng nói theo ngôn ngữ
- ⚙️ Điều chỉnh tốc độ và âm lượng
- 📁 Chọn thư mục lưu file audio

### Command Line Parameters
```
PARAMETER           TYPE  DESCRIPTION
-h, -help           ---   Shows the help info.
-v, -voice          Int   Sets the voice id to use.  
-s, -speed          Int   Sets the TTS voice speed (in percent).  
-vol, -volume       Int   Changes the TTS volume (in decibels).  
-pp, -period-pause  Flt   Sets how long the TTS should pause for at periods (in seconds).  
-cp, -comma-pause   Flt   Sets how long the TTS should pause for at commas (in seconds).  
-lp, -line-pause    Flt   Sets how long the TTS should pause for at newlines (in seconds).
```

Example with parameters:  
`tts.py -v 777 -s 100 -vol 0 -pp 1 -cp 0.5 -lp 2`

## Phân tích Logic Hoạt động (Logic Analysis)

### Tổng quan
Đây là công cụ TTS-Grabber sử dụng API của play.ht để chuyển văn bản thành giọng nói.

### Các thành phần chính
1. **Khởi tạo**: Import thư viện và đọc dữ liệu giọng nói từ `data.json`
2. **Xử lý tham số**: Phân tích tham số dòng lệnh để cấu hình voice, speed, volume
3. **Chọn giọng nói**: Hiển thị danh sách và cho phép người dùng chọn
4. **Đọc văn bản**: Đọc từ `input.txt` và chia thành đoạn 1500 ký tự
5. **Gửi yêu cầu TTS**: POST request đến play.ht API và lưu file MP3

### File data.json
Chứa hơn 800 giọng nói từ các nhà cung cấp:
- Amazon Polly (polly)
- Google Cloud TTS (gc)
- Microsoft Azure TTS (ms)

###### absolutely no api abuse here
