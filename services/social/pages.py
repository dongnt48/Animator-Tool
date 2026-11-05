"""Admin HTML pages, separate from publishing API and browser workers."""
from flask import abort, redirect, render_template, request, url_for
import database


def render_admin(page, title, description):
    return render_template(f'admin/pages/{page}.html', active_page=page,
                           page_title=title, page_description=description)


def overview_page():
    video = request.args.get('video')
    if video:
        return redirect(url_for('social.new_page', video=video))
    return render_admin('overview', 'Tổng quan', 'Theo dõi hoạt động đăng bài đa nền tảng.')


def schedule_page():
    return render_admin('schedule', 'Lịch tự động', 'Chọn giờ một lần. Hệ thống tự lấy bài và đăng.')


def accounts_page():
    return render_admin('accounts', 'Tài khoản', 'Kết nối và quản lý phiên đăng nhập của từng nền tảng.')


def results_page():
    return render_admin('results', 'Kết quả đăng', 'Theo dõi từng lượt đăng và xử lý nền tảng bị lỗi.')


def new_page():
    return render_admin('new', 'Đặt lịch riêng', 'Chọn video và thời gian cho một lượt đăng.')


def captions_page():
    return render_admin('captions', 'AI viết lại caption', 'Chọn video, xem trước và lưu caption mới.')


def video_detail_page(video_id):
    if database.get_video(video_id) is None:
        abort(404)
    return render_template('admin/pages/video-detail.html',active_page='video-detail',
                           page_title='Chi tiết video',page_description='Thông tin, caption và trạng thái đăng của video.',video_id=video_id)


def create_page():
    return render_admin('create','Tạo video','Tải video và dựng hoạt hình với cấu hình của bạn.')


def register_pages(blueprint):
    blueprint.add_url_rule('/create',view_func=create_page)
    blueprint.add_url_rule('/videos/<video_id>',view_func=video_detail_page)
    for route, view in [('', overview_page), ('/schedule', schedule_page),
                        ('/accounts', accounts_page), ('/results', results_page), ('/new', new_page), ('/captions', captions_page)]:
        blueprint.add_url_rule('/publishing' + route, view_func=view)
