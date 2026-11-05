# 🎬 TikTok Animator Studio (2D Cozy Storytelling 9:16)

Hệ thống quản lý, tải và tự động chuyển thể video TikTok sang phong cách **Cozy 2D Animated Storytelling with Kinetic Typography**. Dựng video bằng Remotion trên máy cá nhân; tải video, nhận diện giọng nói qua Google và đăng mạng xã hội cần Internet. Các luồng Playwright không dùng API key của nền tảng.

## Lên lịch đăng mạng xã hội bằng Playwright

Hỗ trợ luồng giao diện cho **Facebook Reels trên hồ sơ cá nhân, Instagram Reels, Threads, TikTok và YouTube**. Một lịch tạo năm tác vụ riêng, dùng caption hiện có (`caption`, nếu có; mặc định là `title` kèm hashtag). Không cần nhập lại caption. Các adapter chưa được kiểm chứng trên tài khoản thật của bạn; giao diện nền tảng có thể cần điều chỉnh selector sau khi thử.

Facebook hiện mở trang tạo Reels bằng hồ sơ đang hoạt động trong phiên trình duyệt đã lưu. Chưa có bộ chọn hoặc xác minh đích Fanpage riêng; hãy chuyển về hồ sơ cá nhân khi kết nối và kiểm tra đúng hồ sơ trước khi lưu phiên. Không suy ra đích đăng chỉ từ tài khoản đăng nhập.

### Cài đặt và chạy trên Windows

### Tự lấy bài theo các giờ trong ngày

Tại `/publishing`, thêm các giờ trong mục **Lịch lặp hằng ngày**, chẳng hạn `08:00`, `12:00`, `19:00`. Mặc định dùng giờ Việt Nam/Bangkok (UTC+7) và **lấy ngẫu nhiên trong video chưa dùng**. Chọn đối tượng khán giả YouTube, bật **Bật đăng tự động hằng ngày**, xác nhận rồi bấm **Lưu lịch hằng ngày**. Không cần chọn video riêng cho mỗi giờ.

Đến mỗi giờ, bộ đăng tự lấy một video đã dựng với caption có sẵn và tạo một lượt gồm cả năm nền tảng. Các video đã từng có lịch hoặc đã được bộ đăng giữ lại sẽ không được tự chọn lại, kể cả lượt đó lỗi/hủy; xử lý nền tảng lỗi trong lượt gốc để tránh đăng trùng. Khi hết video, khung giờ được ghi nhận là **Hết bài** và bỏ qua; video thêm sau đó được xét từ khung giờ kế tiếp.

Thay đổi cấu hình áp dụng từ khi lưu, không chạy bù các giờ trước đó. Sau khi máy tắt hoặc sleep, chỉ khung giờ gần nhất trễ không quá 15 phút mới được lấy bài; các giờ cũ được bỏ qua để không đăng dồn. Tắt tự động chỉ ngừng lấy bài mới, không hủy các lượt đã tạo. Máy và worker cần hoạt động, có mạng; các nền tảng vẫn được xử lý lần lượt. Có thể mở mục **Đặt lịch riêng cho một video (tùy chọn)** nếu muốn lên lịch thủ công.

### Cài đặt và chạy trên Windows

1. Cài Python tương thích với các gói trong `requirements.txt` (môi trường phát triển đã kiểm tra Python 3.15).
2. Chạy `setup.bat` một lần để tạo `.venv`, cài dependency và Chromium của Playwright.
3. Khởi động lại ứng dụng bằng `run.bat`. Mở `http://localhost:5000/publishing`, hoặc chọn **Lên lịch đăng mạng xã hội** trong thư viện.
4. Với từng nền tảng, chọn **Kết nối**, đăng nhập thủ công trong cửa sổ vừa mở, kiểm tra đúng tài khoản/hồ sơ/kênh rồi quay lại Studio bấm **Lưu phiên**. Thực hiện xác minh/2FA trực tiếp khi nền tảng yêu cầu. Mỗi lần kết nối có tối đa 20 phút.
5. Chọn video đã dựng, kiểm tra video và caption, chọn ngày/giờ và đối tượng trẻ em của YouTube, xác nhận rồi bấm **Lên lịch cho cả 5 nền tảng**. YouTube dùng dòng đầu caption làm tiêu đề (tối đa 100 ký tự) và giữ toàn bộ caption trong mô tả; xuất bản công khai.

Máy phải bật, không sleep và có mạng. Bộ đăng xử lý lần lượt để hạn chế tải bộ nhớ; giờ xuất hiện công khai không được đảm bảo đồng thời. Đóng trang web không hủy các lịch: bộ đăng là tiến trình riêng. Dùng **Hủy phần chưa chạy** để dừng các đích còn chờ; tác vụ đã bắt đầu không bị hủy giữa chừng.

### Trạng thái, thử lại và tránh đăng trùng

- Mỗi nền tảng có trạng thái và link riêng. Chỉ báo **Đã đăng** khi có thông báo hoàn thành cùng permalink trong giao diện xác nhận của nền tảng.
- Nếu lỗi trước bước xuất bản, có thể thử lại riêng nền tảng đó. Phiên hết hạn sẽ yêu cầu kết nối lại.
- Nếu đã bắt đầu bấm xuất bản nhưng chưa nhận được kết quả, chuyển sang **Cần kiểm tra bài**. Mở tài khoản để kiểm tra: nếu đã đăng, dùng **Bài đã đăng • lưu link**; nếu chắc chắn chưa có, dùng **Đã kiểm tra, thử lại**. Không tự động lặp lại thao tác xuất bản.
- Lịch trễ hơn 15 phút (máy tắt/sleep hoặc hàng đợi chậm) cần xác nhận lại thay vì tự động đăng muộn.
- Lịch giữ một bản sao MP4 và caption riêng. Dựng lại/xóa video gốc không đổi lịch đã tạo. Nếu bản sao bị thay đổi, worker dừng tác vụ.
- Khi xác định được ID tài khoản/kênh, lịch gắn với tài khoản lúc tạo. Đổi tài khoản sẽ yêu cầu kết nối lại tài khoản cũ hoặc tạo lịch mới. Kiểm tra tài khoản khi lưu phiên, đặc biệt nếu dùng nhiều kênh YouTube.

### Dữ liệu cục bộ và bộ đăng

SQLite, hồ sơ trình duyệt, bản sao MP4, log và ảnh chụp lỗi nằm trong `data/social/`, đã được loại khỏi Git. Không chia sẻ thư mục này vì hồ sơ chứa phiên đăng nhập. Ảnh chụp lỗi: `data/social/diagnostics/<task-id>.png`; log tiến trình: `data/social/process.log`. Bản sao video được giữ lại để bảo toàn lịch; chỉ dọn khi không còn lịch cần dùng chúng.

`run.bat` dùng Python trong `.venv` nếu có và tự khởi động bộ đăng. Có thể chạy bộ đăng thủ công:

```powershell
.\.venv\Scripts\python.exe -m services.social.worker
```

Chỉ một worker được hoạt động cho cùng thư mục dữ liệu; khóa hệ điều hành ngăn tiến trình thứ hai xử lý trùng. Để chạy Studio mà không tự mở worker, đặt `SOCIAL_AUTOSTART_WORKER=0` trước khi chạy `app.py`. `SOCIAL_DATA_DIR` cho phép chỉ định thư mục dữ liệu riêng; Studio, login và worker phải dùng chung thư mục này. Web chỉ nghe `127.0.0.1` và nhận các thao tác từ cùng nguồn localhost.

Engine render vẫn cần dự án Node/Remotion tại `../remotion-project` cùng dependency của nó; phần này nằm ngoài repo hiện tại. Không cần engine để mở trang lịch và quản lý các video đã dựng sẵn.

### Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/admin/js/core.js
```

Kiểm tra dùng SQLite tạm, MP4 thử và Playwright headless trên trang HTML cục bộ; không đăng nhập hoặc đăng bài thật. Môi trường chưa cài Playwright sẽ bỏ qua các kiểm tra trình duyệt. Chạy `setup.bat` để chạy đủ.

### Các trang quản trị

- `/publishing`: Tổng quan.
- `/publishing/schedule`: Lịch tự động hằng ngày.
- `/publishing/accounts`: Kết nối tài khoản.
- `/publishing/results`: Kết quả và thử lại nền tảng lỗi.
- `/publishing/new`: Đặt lịch riêng cho một video.
- `/publishing/captions`: Chọn video và nhờ AI viết lại caption.

### Trạng thái đăng và caption AI

Thư viện video có cột **Đã đăng ở đâu**, hiển thị kết quả riêng cho Facebook, Instagram, Threads, TikTok và YouTube. Bài đã xuất bản có link mở bài. Trạng thái được lấy từ toàn bộ lịch sử của video; chỉ đánh dấu đã đăng khi worker có xác nhận hoặc bạn đã xác nhận thủ công bằng link bài.

Trong **Thư viện**, tích chọn ngay trong bảng (hoặc chọn tất cả), rồi bấm **Viết lại caption** trên thanh caption. Nút **Viết lại caption** của từng dòng chạy ngay cho video đó, không thay đổi lựa chọn hoặc chuyển màn; thao tác riêng từng dòng cho phép viết lại cả video đã viết, không phụ thuộc bộ lọc xử lý hàng loạt. Nút hiện **Đang viết…** trong khi xử lý. **AI viết thành công là lưu trực tiếp vào video, cập nhật ngay nội dung trong bảng; không có bản nháp hoặc bước duyệt/lưu thêm.** AI không tự tạo hoặc giữ hashtag cũ trong kết quả mới. Bấm tiêu đề/dòng để xem video gốc/đã dựng, thông tin dựng, caption hiện tại, lời thoại và trạng thái đăng. Vẫn có thể sửa caption thủ công ở màn chi tiết rồi bấm lưu. Nếu caption đã thay đổi trong lúc AI chạy, hệ thống báo lỗi video đó và không ghi đè. Đường dẫn `/publishing/captions` cũ vẫn dùng được để tương thích; kết quả AI ở đó cũng đã lưu trực tiếp.

Nút **Lên lịch đăng** của từng dòng mở hộp chọn giờ ngay trong Thư viện: xem caption sẽ đăng, chọn thời gian, phân loại nội dung YouTube và xác nhận đăng cả 5 nền tảng. Bấm **Lưu lịch đăng** để tạo lịch mà không chuyển màn. Nếu mất phản hồi, thử lại trong cùng hộp với dữ liệu không đổi dùng cùng mã yêu cầu để tránh tạo lịch trùng. Màn Đặt lịch riêng cũ vẫn hoạt động.

Hai màn riêng trong thanh bên: **Tạo video** (`/create`) gồm tải/dựng, cấu hình mặc định, thống kê và tiến trình xử lý; **Thư viện** (`/`) gồm bảng quản lý video, viết caption và trạng thái đăng. Màn tạo không tải phần cấu hình caption; thư viện không có ô nhập link/tải video. Các nút dựng lại từng video vẫn có trong thư viện.

Trong bảng thư viện, tiêu đề chỉ hiện tối đa hai dòng với dấu “…”, rê chuột để đọc đầy đủ. Cột **Video gốc** và **Thành phẩm** có thumbnail lấy từ đúng file video trên máy; bấm ảnh để mở trình phát. Không còn cột Xem trước hoặc nút Chi tiết; bấm vào nội dung dòng (hoặc Enter khi dòng được chọn) để mở record. Các ô chọn, dropdown, nút và liên kết vẫn thao tác riêng. Thumbnail được tạo và lưu đệm trong `data/social/thumbnails`, tự tạo lại khi file nguồn thay đổi.

Khi khởi động bản mới, các bản nháp cũ còn khớp caption gốc được áp dụng trực tiếp; bản cũ đã lệch caption hiện tại được bỏ qua. Trước khi chuyển đổi, hệ thống sao lưu thư viện vào `data/social/videos-before-direct-captions.json`. Bản gốc `title` và caption đã chốt trong các lịch đăng hiện có được giữ nguyên.

Trong **Tùy chỉnh → Hashtag mặc định**, nhập bộ hashtag của bạn rồi bấm **Lưu hashtag**. Có thể nhập có/không có dấu `#`, tách bằng khoảng trắng, dấu phẩy hoặc xuống dòng; hệ thống chuẩn hóa và bỏ trùng. Để trống thì caption mới không có hashtag. Thay đổi chưa lưu được lưu khi bấm viết lại; toàn bộ batch trong một lượt dùng cùng bộ hashtag đó. Cài đặt được nhớ trong SQLite trên máy. Hashtag do AI sinh ra được loại bỏ trước khi ghép đúng hashtag bạn đã nhập. Cài đặt chỉ áp dụng cho lần viết lại tiếp theo, không tự sửa caption đã có hoặc lịch đã tạo. Nếu tự gõ hashtag khi chỉnh caption ở màn chi tiết, thao tác lưu vẫn giữ nguyên.

Thanh caption gọn có hai chế độ trên các video đang chọn: **Chỉ chưa viết lại** (mặc định, bỏ qua caption đã viết lại) hoặc **Viết lại tất cả đã chọn**. Số “sẽ viết” cho biết số video thực sự được xử lý. Bấm **Viết lại caption** để chạy. Backend kiểm tra lại trạng thái trước khi nhận diện/gọi AI, nên video vừa được xử lý ở nơi khác cũng được bỏ qua trong chế độ chưa viết lại. Yêu cầu thêm và hướng dẫn nằm trong **Tùy chỉnh**.

Giao diện chia lần lượt thành các batch tối đa 100 video; mỗi batch gửi chung **một request AI** tới `https://api.xah.io/v1/chat/completions`, dùng model đã cấu hình (mặc định `gemini-3.8-flash`). Kết quả ghép bằng ID video, không dựa vào thứ tự. ID thiếu/trùng hoặc caption lỗi được báo riêng. Không tự thử lại hoặc chuyển sang gọi AI từng video. Kết quả batch trước vẫn giữ nếu batch sau gặp lỗi. Việc sử dụng API có thể tính phí theo tài khoản của bạn.

Vào **Tùy chỉnh → Cấu hình AI**, nhập **Model** và **API key**, rồi bấm **Lưu cấu hình AI**. Model phải được XAH hỗ trợ. Để trống ô API key để giữ khóa hiện tại; ô mật khẩu tự xóa sau khi lưu và khóa đã lưu không được trả lại qua API. Cấu hình được lưu cục bộ trong SQLite thuộc `data/social/` (đã được Git bỏ qua). Khóa nhập trong giao diện được ưu tiên; nếu chưa lưu khóa thì vẫn dùng biến môi trường `XAH_API_KEY` hoặc `.env` ở thư mục gốc (xem `.env.example`). Thay đổi chưa lưu cũng được lưu khi bấm viết lại; backend đọc model/key một lần cho mỗi batch. Việc lưu chỉ xác nhận cấu hình, không gọi nhà cung cấp để kiểm tra khóa/model.

Caption mới lưu trong trường `caption`, tiêu đề gốc vẫn được giữ. Các lịch đã tạo giữ nguyên bản caption đã chốt; lịch mới và bộ lấy bài tự động dùng caption mới.

Mặc định tab AI bật **Dùng lời thoại video**: gửi văn bản lời thoại, caption hiện tại và yêu cầu của bạn cho XAH. Video chưa lưu thoại sẽ nhận diện âm thanh qua Google Speech Recognition khi bấm viết lại; thoại thật được lưu trong thư viện để lần sau dùng lại. Video dựng mới cũng lưu thoại từ bước nhận diện. Không gửi câu mẫu của engine dựng phim như thể đó là lời thoại thật. Nếu nhận diện lỗi, AI không được gọi cho video đó.

Mỗi video gửi tối đa **300 ký tự đầu của lời thoại**, bản thoại đầy đủ vẫn được lưu. Màn chi tiết cho xem đoạn thoại đã gửi. Đây là giới hạn đầu vào do ứng dụng chọn, không phải giới hạn ngữ cảnh của nhà cung cấp. Có thể tắt lời thoại để chỉ viết lại caption. XAH không nhận file âm thanh/video; Google nhận âm thanh khi cần nhận diện. Việc nhận diện có thể lâu hơn viết lại caption đơn thuần. Giữ trang mở đến khi các batch hoàn thành; caption của những batch đã thành công được giữ khi tải lại trang, các batch chưa chạy không tự khởi động lại.

Sau khi cập nhật từ giao diện một trang, đóng Studio cũ và chạy lại `run.bat` để nạp các route mới. Cấu trúc template, module JavaScript và backend được mô tả trong [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

---

## 🌟 Tính Năng Nổi Bật

1. **Quản Lý Nội Dung Trực Quan (GUI Dashboard):**
   - Bảng quản lý thông minh với số thứ tự (STT), hình thu nhỏ (Thumbnail), tiêu đề, thời lượng và trạng thái xử lý theo thời gian thực (Mới tải về 🟡, Đang dựng 🔵, Đã hoàn thành 🟢, Lỗi 🔴).
   - Xem video TikTok gốc ngay trên trình duyệt (không watermark).
   - Xem và tải video hoạt hình thành phẩm chuẩn 9:16 trực tiếp.

2. **Tải Video & Kênh TikTok Tự Động:**
   - Hỗ trợ tải video riêng lẻ từ link TikTok.
   - Hỗ trợ tải hàng loạt video từ một kênh (ví dụ: `@60daykyluat`) với tùy chọn số lượng (1, 3, 5, 10, 20 video).

3. **Chuyển Thể Hoạt Hình 2D Cozy Storytelling (Remotion Engine):**
   - **Giữ nguyên 100% âm thanh gốc** (giọng đọc, nhạc nền cảm xúc).
   - **Trích xuất giọng nói & Tách câu theo nhịp**: Tự động nhận diện tiếng Việt và căn chỉnh thời gian xuất hiện từng từ khóa.
   - **Nhận diện cảm xúc (Mood Detection)**: Tự động phân tích nội dung để chọn hành động cho nhân vật người que (suy ngẫm `reflecting`, kiên định `loyal`, xúc động `sad`, bình an `peace`, bài học `regret`, tự hào `proud`).
   - **Kinetic Typography 2 Tầng**: Dòng chữ nói ngữ cảnh + Huy hiệu pill phóng to giật nảy (Spring physics) không lo bị đè chữ.
   - **Cozy Sticky Notes**: Tờ giấy note dán băng keo Washi đung đưa hiển thị thông điệp cốt lõi của từng phân cảnh.
   - **Hiệu ứng môi trường Cozy**: Đèn đom đóm lung linh treo trần nhà, ly cà phê bốc khói nghi ngút, đốm sáng lấp lánh nhẹ nhàng.

4. **Dựng video cục bộ:**
   - Phần dựng chạy trên máy; viết caption qua XAH cần API key và có thể tính phí.
   - Kết xuất trực tiếp qua Remotion Engine & GPU/CPU máy tính cá nhân.

---

## 🚀 Hướng Dẫn Khởi Động

### Cách 1: Chạy Bằng File Batch (Khuyên dùng)
Nhấp đúp chuột vào file:
```
TikTok_Animator_Studio\run.bat
```
Trình duyệt sẽ tự động mở trang web quản trị tại: `http://localhost:5000`

### Cách 2: Chạy Bằng Terminal / PowerShell
```powershell
cd c:\Users\nguye\Desktop\Video\TikTok_Animator_Studio
python app.py
```
Sau đó truy cập: `http://localhost:5000`

---

## 📁 Cấu Trúc Dự Án

Xem [cấu trúc thư mục hiện tại](docs/PROJECT_STRUCTURE.md).
