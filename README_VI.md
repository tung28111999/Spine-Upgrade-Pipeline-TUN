# Spine Upgrade Pipeline TUN - Hướng Dẫn Sử Dụng

Spine Upgrade Pipeline TUN là công cụ desktop viết bằng Python/PySide6, hỗ trợ nâng phiên bản dữ liệu Spine khi không còn file dự án gốc `.spine`.

Công cụ được thiết kế cho trường hợp bạn chỉ còn bộ dữ liệu đã xuất ra, gồm:

- `.json` hoặc `.skel.bytes`
- `.atlas.txt`
- ảnh atlas PNG

Mục tiêu chính là tự động hóa quy trình nâng phiên bản Spine để sử dụng lại trong Unity hoặc các pipeline runtime khác.

## Công Cụ Hỗ Trợ Những Gì?

- Nâng cấp phiên bản của file Spine lên phiên bản cao hơn với các bộ dữ liệu `.json` hoặc `.skel.bytes`, `.atlas.txt`, và ảnh atlas PNG.
- Tự nhận diện phiên bản Spine cũ từ file `.json` hoặc `.skel.bytes`.
- Tạo bản sao dữ liệu vào vùng xử lý tạm, không chỉnh sửa file gốc.
- Sử dụng Spine CLI để import dữ liệu runtime cũ.
- Xuất lại dữ liệu runtime bằng phiên bản Spine đích.
- Tạo bộ output sẵn sàng sử dụng:
  - `.json` hoặc `.skel.bytes`
  - `.atlas.txt`
  - ảnh atlas PNG
- Hỗ trợ xử lý một asset, nhiều thư mục asset, file `.zip`, và file `.rar`.
- Tạo file `.spine` phiên bản mới khi dữ liệu đầu vào cho phép.

## Lưu Ý Quan Trọng

- Công cụ này không bao gồm Spine.
- Người dùng cần tự cài Spine và sử dụng license Spine hợp lệ.
- Trước khi chạy, nên mở Spine Launcher và kiểm tra các phiên bản Spine cần dùng đã chạy được bình thường.
- File `.spine` được tạo lại có thể không khôi phục chính xác 100% dự án gốc nếu dữ liệu runtime ban đầu thiếu thông tin dành cho editor hoặc nonessential data.
- Đây là công cụ độc lập, không liên kết và không được bảo trợ bởi Esoteric Software.

## Tuyên Bố Miễn Trừ

Đây là công cụ cộng đồng không chính thức. Công cụ này không liên kết, không được xác nhận, và không được bảo trợ bởi Esoteric Software.

Spine là sản phẩm thương mại riêng của Esoteric Software. Repository này không bao gồm Spine, Spine CLI, file thực thi Spine, hoặc bất kỳ file license Spine nào.

Người dùng cần tự cài Spine riêng và sử dụng license Spine hợp lệ của mình.

Khi import dữ liệu skeleton đã export ngược trở lại Spine, project `.spine` được dựng lại có thể không khớp hoàn toàn với project gốc nếu thiếu nonessential/editor data.

## Yêu Cầu

- Windows
- Python 3.10 trở lên
- PySide6
- Spine đã được cài trên máy và có license hợp lệ
- Nếu xử lý file `.rar`: cần 7-Zip, WinRAR, hoặc unrar

Cài đặt thư viện:

```powershell
python -m pip install -r requirements.txt
```

## Cấu Hình Spine

Sao chép file cấu hình mẫu:

```powershell
copy config.example.json config.json
```

Sau đó chỉnh `config.json` để trỏ tới đường dẫn Spine trên máy:

```json
{
  "spine_versions": {
    "3.7": "C:/Program Files/Spine/Spine.com",
    "3.8": "C:/Program Files/Spine/Spine.com",
    "4.0": "C:/Program Files/Spine/Spine.com",
    "4.1": "C:/Program Files/Spine/Spine.com",
    "4.2": "C:/Program Files/Spine/Spine.com"
  }
}
```

Khuyến nghị dùng `Spine.com` cho chế độ dòng lệnh. Với giao diện desktop, chọn `Spine.exe` cũng được hỗ trợ.

## Chạy Giao Diện Desktop

```powershell
python main.py
```

Trong giao diện, chọn:

- Kiểu dữ liệu đầu vào: thư mục hoặc file `.zip` / `.rar`
- Đường dẫn dữ liệu đầu vào
- File thực thi Spine
- Phiên bản Spine đích

Kết quả được tạo tại:

```text
<thư-mục-đầu-vào>/SpineNewVersion/
```

Cấu trúc output chính:

```text
SpineNewVersion/
  export/
  spine_new/
  export.zip
  spine_new.zip
```

## Ví Dụ Dữ Liệu Đầu Vào

```text
Boss_A/
  Boss_A.skel.bytes
  Boss_A.atlas.txt
  Boss_A.png
```

hoặc:

```text
Boss_A/
  Boss_A.json
  Boss_A.atlas.txt
  Boss_A.png
```

## Chạy Bằng Dòng Lệnh

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack
```

Xuất dữ liệu dạng JSON:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-json --pack
```

Chế độ nhanh, chỉ xuất runtime và không tạo project `.spine` mới:

```powershell
python run_pipeline.py --input "D:/asset/Boss_A" --output "D:/out/Boss_A" --new 4.1 --export-binary --pack --skip-spine-new
```

## Đóng Gói Ứng Dụng

Xem thêm tại [README_BUILD.md](README_BUILD.md).

Lệnh build nhanh:

```powershell
python -m pip install pyinstaller
build_windows.bat
```

Kết quả build:

```text
dist/SpineUpgradePipelineTUN/
```

Ứng dụng sau khi build không bao gồm file thực thi Spine hoặc license Spine.

## Đóng Góp

Mọi đóng góp đều được hoan nghênh.

Vui lòng:

- Không đưa file thực thi Spine hoặc file license Spine vào repository.
- Giữ thay đổi trong pipeline tương thích ngược nếu có thể.
- Kiểm thử bằng một project mẫu nhỏ trước khi mở pull request.

## License

Mã nguồn của công cụ được phát hành theo giấy phép MIT. Spine là phần mềm thương mại riêng và không được đính kèm trong dự án này.
