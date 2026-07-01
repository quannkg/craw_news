from __future__ import annotations

import html
import math
import sys
import webbrowser

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.crawlers.registry import list_sources
from app.db.database import DB_PATH, ensure_database
from app.services.crawl_service import CrawlService


APP_STYLE = """
QMainWindow {
    background: #f4efe6;
}
QWidget {
    color: #2b2118;
    font-size: 13px;
}
QGroupBox {
    background: #fffaf3;
    border: 1px solid #e4d6c3;
    border-radius: 16px;
    margin-top: 14px;
    font-weight: 600;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #7a4b2a;
}
QLabel[role="title"] {
    font-size: 26px;
    font-weight: 700;
    color: #5b331b;
}
QLabel[role="subtitle"] {
    color: #80634e;
    font-size: 13px;
}
QLabel[role="caption"] {
    color: #8d7461;
    font-size: 12px;
}
QLabel[role="status"] {
    background: #f8ecdd;
    border: 1px solid #edd3b5;
    border-radius: 12px;
    padding: 10px 12px;
    color: #6d4427;
    font-weight: 600;
}
QFrame[role="card"] {
    background: #fffaf3;
    border: 1px solid #e4d6c3;
    border-radius: 18px;
}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTableWidget, QTextBrowser {
    background: #fffdf9;
    border: 1px solid #dbc7ae;
    border-radius: 10px;
    padding: 8px 10px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #bb6c38;
}
QPushButton {
    background: #ead8c2;
    border: none;
    border-radius: 12px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #dfc4a5;
}
QPushButton:disabled {
    background: #eee5da;
    color: #9a8d80;
}
QPushButton[variant="primary"] {
    background: #a85024;
    color: white;
}
QPushButton[variant="primary"]:hover {
    background: #91451e;
}
QPushButton[variant="danger"] {
    background: #5f6f52;
    color: white;
}
QPushButton[variant="danger"]:hover {
    background: #526147;
}
QCheckBox {
    spacing: 8px;
}
QProgressBar {
    background: #f1e4d4;
    border: none;
    border-radius: 9px;
    min-height: 18px;
    text-align: center;
    color: #5b331b;
    font-weight: 600;
}
QProgressBar::chunk {
    background: #c26a37;
    border-radius: 9px;
}
QHeaderView::section {
    background: #f3e3cf;
    color: #6d4427;
    border: none;
    border-right: 1px solid #e4d6c3;
    border-bottom: 1px solid #e4d6c3;
    padding: 10px;
    font-weight: 700;
}
QTableWidget {
    gridline-color: #eedfcd;
    selection-background-color: #f0d3b6;
    selection-color: #34251b;
}
QDialog {
    background: #f6f0e7;
}
QTabWidget::pane {
    border: 1px solid #e4d6c3;
    border-radius: 14px;
    background: #fffaf3;
    top: -1px;
}
QTabBar::tab {
    background: #ead8c2;
    color: #6d4427;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 16px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #fffaf3;
    color: #a85024;
}
"""


class CrawlWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        service: CrawlService,
        source_name: str,
        crawl_type: str,
        url: str,
        max_pages: int,
        max_articles: int,
        crawl_comments: bool,
        force_refresh: bool,
    ) -> None:
        super().__init__()
        self.service = service
        self.source_name = source_name
        self.crawl_type = crawl_type
        self.url = url
        self.max_pages = max_pages
        self.max_articles = max_articles
        self.crawl_comments = crawl_comments
        self.force_refresh = force_refresh

    def run(self) -> None:
        try:
            result = self.service.crawl_source(
                source_name=self.source_name,
                url=self.url,
                crawl_type=self.crawl_type,
                max_pages=self.max_pages,
                max_articles=self.max_articles,
                crawl_comments=self.crawl_comments,
                force_refresh=self.force_refresh,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class ArticleDetailDialog(QDialog):
    def __init__(self, article: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.article = article
        self.setWindowTitle(article.get("title", "Chi tiết bài viết"))
        self.resize(920, 760)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._build_article_html())
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        open_button = QPushButton("Mở link gốc")
        open_button.clicked.connect(self._open_source_url)
        buttons.addButton(open_button, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_article_html(self) -> str:
        title = html.escape(self.article.get("title", ""))
        description = html.escape(self.article.get("description", ""))
        author = html.escape(self.article.get("author", ""))
        category = html.escape(self.article.get("category", ""))
        published = html.escape(
            self.article.get("published_time_text")
            or self.article.get("published_at")
            or ""
        )
        source_url = html.escape(self.article.get("source_url", ""))
        content = self.article.get("content", "")
        images = self.article.get("images", [])
        comments = self.article.get("comments", [])

        paragraph_html = "".join(
            f"<p>{html.escape(part.strip())}</p>"
            for part in content.split("\n\n")
            if part.strip()
        )
        image_html = "".join(
            (
                "<figure>"
                f"<img src='{html.escape(image.get('image_url', ''))}' "
                "style='max-width:100%; border-radius:14px; margin:12px 0 8px 0;'/>"
                f"<figcaption>{html.escape(image.get('caption', ''))}</figcaption>"
                "</figure>"
            )
            for image in images
            if image.get("image_url")
        )
        comments_html = self._build_comments_html(comments)

        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Georgia, 'Times New Roman', serif;
                    color: #2d2119;
                    background: #fffdf8;
                    margin: 0;
                    padding: 20px 28px;
                    line-height: 1.7;
                }}
                .meta {{
                    color: #866a57;
                    font-size: 13px;
                    margin-bottom: 20px;
                }}
                h1 {{
                    font-size: 30px;
                    line-height: 1.25;
                    color: #512b18;
                    margin-bottom: 10px;
                }}
                .desc {{
                    font-size: 17px;
                    color: #5f483a;
                    font-weight: bold;
                    margin-bottom: 18px;
                }}
                p {{
                    font-size: 18px;
                    margin: 0 0 16px 0;
                }}
                figcaption {{
                    color: #776255;
                    font-size: 13px;
                    font-style: italic;
                    margin-bottom: 14px;
                }}
                .footer {{
                    margin-top: 28px;
                    padding-top: 14px;
                    border-top: 1px solid #eadbc9;
                    font-size: 13px;
                }}
                .comments {{
                    margin-top: 34px;
                    padding-top: 20px;
                    border-top: 2px solid #eadbc9;
                }}
                .comment-item {{
                    background: #fff8ef;
                    border: 1px solid #efdcca;
                    border-radius: 14px;
                    padding: 14px 16px;
                    margin-bottom: 12px;
                }}
                .comment-meta {{
                    color: #7b6455;
                    font-size: 13px;
                    margin-bottom: 8px;
                }}
                .comment-user {{
                    font-weight: bold;
                    color: #54301e;
                }}
                .comment-content {{
                    font-size: 15px;
                    line-height: 1.65;
                }}
            </style>
        </head>
        <body>
            <div class="meta">{category} | {published}</div>
            <h1>{title}</h1>
            <div class="desc">{description}</div>
            {image_html}
            {paragraph_html}
            {comments_html}
            <div class="footer">
                <strong>Tác giả:</strong> {author}<br/>
                <strong>Nguồn:</strong>
                <a href="{source_url}">{source_url}</a>
            </div>
        </body>
        </html>
        """

    def _build_comments_html(self, comments: list[dict]) -> str:
        if not comments:
            return ""

        items = []
        for comment in comments:
            level = int(comment.get("level", 0) or 0)
            margin_left = level * 24
            username = html.escape(comment.get("username", "") or "Ẩn danh")
            time_text = html.escape(comment.get("comment_time_text", ""))
            content = html.escape(comment.get("content", ""))
            like_count = int(comment.get("like_count", 0) or 0)
            reply_count = int(comment.get("reply_count", 0) or 0)
            items.append(
                f"""
                <div class="comment-item" style="margin-left:{margin_left}px;">
                    <div class="comment-meta">
                        <span class="comment-user">{username}</span>
                        {' | ' + time_text if time_text else ''}
                        | Thích: {like_count}
                        | Phản hồi: {reply_count}
                    </div>
                    <div class="comment-content">{content}</div>
                </div>
                """
            )

        return f"""
        <div class="comments">
            <h2 style="font-size:24px; color:#5b331b; margin-bottom:18px;">Bình luận</h2>
            {''.join(items)}
        </div>
        """

    def _open_source_url(self) -> None:
        source_url = self.article.get("source_url", "").strip()
        if source_url:
            webbrowser.open(source_url)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ensure_database()
        self.service = CrawlService()
        self.worker_thread: QThread | None = None
        self.worker: CrawlWorker | None = None
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self._update_progress_ui)
        self._last_progress_snapshot: tuple = ()
        self.current_page = 1
        self.page_size = 15
        self.total_pages = 1
        self.current_rows: list[dict] = []
        self.is_local_search_mode = False
        self.setWindowTitle("CrawBao")
        self.resize(1480, 900)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._load_filter_options()
        self._load_articles()

    def _build_ui(self) -> None:
        root = QWidget()
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        main_layout.addWidget(self._build_header_card())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        content_layout.addWidget(self._build_left_panel(), 4)
        content_layout.addWidget(self._build_right_panel(), 8)
        main_layout.addLayout(content_layout)

        self.setCentralWidget(root)
        self._handle_source_changed(self.source_select.currentText())

    def _build_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title = QLabel("CrawBao")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Crawl báo bằng Python, lưu SQLite local, duyệt dữ liệu theo kiểu thư viện bài viết."
        )
        subtitle.setProperty("role", "subtitle")
        db_label = QLabel(f"Cơ sở dữ liệu: {DB_PATH}")
        db_label.setProperty("role", "caption")
        db_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(db_label)
        return card

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_control_group())
        layout.addWidget(self._build_status_group())
        layout.addStretch(1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_library_group(), 7)
        layout.addWidget(self._build_log_group(), 3)
        return panel

    def _build_control_group(self) -> QGroupBox:
        group = QGroupBox("Điều khiển crawl")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(14)

        self.source_select = QComboBox()
        self.source_select.addItems(list_sources())
        self.source_select.currentTextChanged.connect(self._handle_source_changed)

        self.max_pages_input = QSpinBox()
        self.max_pages_input.setRange(1, 999)
        self.max_pages_input.setValue(3)

        self.max_articles_input = QSpinBox()
        self.max_articles_input.setRange(0, 10000)
        self.max_articles_input.setValue(20)
        self.max_articles_input.setSpecialValueText("Không giới hạn")

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(12)
        top_grid.setVerticalSpacing(10)
        top_grid.addWidget(QLabel("Nguồn dữ liệu"), 0, 0)
        top_grid.addWidget(self.source_select, 0, 1)
        top_grid.addWidget(QLabel("Số trang tối đa"), 1, 0)
        top_grid.addWidget(self.max_pages_input, 1, 1)
        top_grid.addWidget(QLabel("Số bài tối đa"), 2, 0)
        top_grid.addWidget(self.max_articles_input, 2, 1)
        layout.addLayout(top_grid)

        self.control_tabs = QTabWidget()
        self.control_tabs.currentChanged.connect(self._handle_control_tab_changed)
        self.control_tabs.addTab(self._build_url_crawl_tab(), "Crawl theo URL")
        self.control_tabs.addTab(self._build_keyword_crawl_tab(), "VNExpress theo từ khóa")
        layout.addWidget(self.control_tabs)

        self.crawl_comments_checkbox = QCheckBox("Crawl comment nếu có")
        self.force_refresh_checkbox = QCheckBox("Crawl lại bài đã tồn tại")
        layout.addWidget(self.crawl_comments_checkbox)
        layout.addWidget(self.force_refresh_checkbox)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.crawl_button = QPushButton("Bắt đầu crawl")
        self.crawl_button.setProperty("variant", "primary")
        self.crawl_button.clicked.connect(self._handle_crawl)

        self.stop_button = QPushButton("Dừng")
        self.stop_button.setProperty("variant", "danger")
        self.stop_button.clicked.connect(self._handle_stop)
        self.stop_button.setEnabled(False)

        self.refresh_button = QPushButton("Tải lại dữ liệu")
        self.refresh_button.clicked.connect(self._handle_refresh_all)

        button_row.addWidget(self.crawl_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.refresh_button)
        layout.addLayout(button_row)

        hint = QLabel(
            "Gợi ý: test theo thứ tự menu VNExpress -> category -> article -> từ khóa -> comment."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "caption")
        layout.addWidget(hint)
        return group

    def _build_url_crawl_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        self.url_crawl_type_select = QComboBox()
        self.url_crawl_type_select.addItems(["article", "category", "menu"])
        self.url_crawl_type_select.currentTextChanged.connect(self._handle_url_crawl_type_changed)

        self.url_input = QLineEdit("https://example.com")
        self.url_input.setPlaceholderText("Nhập URL cần crawl")

        self.url_label = QLabel("URL")
        layout.addWidget(QLabel("Loại crawl"), 0, 0)
        layout.addWidget(self.url_crawl_type_select, 0, 1)
        layout.addWidget(self.url_label, 1, 0)
        layout.addWidget(self.url_input, 1, 1)
        return tab

    def _build_keyword_crawl_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        self.keyword_crawl_source_label = QLabel("Nguồn tìm kiếm")
        self.keyword_crawl_source_value = QLabel("VNExpress Search")
        self.keyword_crawl_source_value.setStyleSheet("font-weight: 700; color: #5b331b;")

        self.keyword_crawl_input = QLineEdit()
        self.keyword_crawl_input.setPlaceholderText("Nhập từ khóa, ví dụ: kẹo Kera")

        layout.addWidget(self.keyword_crawl_source_label, 0, 0)
        layout.addWidget(self.keyword_crawl_source_value, 0, 1)
        layout.addWidget(QLabel("Từ khóa tìm kiếm"), 1, 0)
        layout.addWidget(self.keyword_crawl_input, 1, 1)
        return tab

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("Trạng thái")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        self.status_label = QLabel("Sẵn sàng.")
        self.status_label.setProperty("role", "status")
        self.status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        self.current_url_value = self._create_info_box("URL hiện tại", "Chưa có")
        self.article_count_value = self._create_info_box("Đã xử lý", "0 bài")
        self.error_count_value = self._create_info_box("Lỗi", "0")
        summary_row.addWidget(self.current_url_value["frame"], 2)
        summary_row.addWidget(self.article_count_value["frame"], 1)
        summary_row.addWidget(self.error_count_value["frame"], 1)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(summary_row)
        return group

    def _build_library_group(self) -> QGroupBox:
        group = QGroupBox("Thư viện bài viết")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.local_search_input = QLineEdit()
        self.local_search_input.setPlaceholderText("Tìm trong dữ liệu đã lưu...")
        self.local_search_input.returnPressed.connect(self._apply_local_search)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Tìm theo tiêu đề, mô tả, nội dung, link...")
        self.keyword_input.returnPressed.connect(self._apply_filters)

        self.source_filter = QComboBox()
        self.source_filter.addItems(["Tất cả nguồn", "vnexpress"])
        self.source_filter.currentTextChanged.connect(self._apply_filters)

        self.category_filter = QComboBox()
        self.category_filter.addItem("Tất cả chuyên mục")
        self.category_filter.currentTextChanged.connect(self._apply_filters)

        self.page_size_select = QComboBox()
        self.page_size_select.addItems(["10", "15", "20", "30", "50"])
        self.page_size_select.setCurrentText("15")
        self.page_size_select.currentTextChanged.connect(self._handle_page_size_changed)

        local_search_button = QPushButton("Tìm local")
        local_search_button.clicked.connect(self._apply_local_search)

        filter_button = QPushButton("Lọc danh sách")
        filter_button.clicked.connect(self._apply_filters)

        filter_row.addWidget(self.local_search_input, 2)
        filter_row.addWidget(local_search_button)
        filter_row.addWidget(self.keyword_input, 3)
        filter_row.addWidget(self.source_filter, 1)
        filter_row.addWidget(self.category_filter, 1)
        filter_row.addWidget(self.page_size_select)
        filter_row.addWidget(filter_button)
        layout.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Tiêu đề", "Chuyên mục", "Thời gian đăng", "Thời gian crawl", "Link nguồn"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._show_selected_article)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        self.pagination_label = QLabel("Trang 1/1")
        self.pagination_label.setProperty("role", "caption")

        self.prev_page_button = QPushButton("Trang trước")
        self.prev_page_button.clicked.connect(self._go_prev_page)

        self.next_page_button = QPushButton("Trang sau")
        self.next_page_button.clicked.connect(self._go_next_page)

        self.view_button = QPushButton("Xem bài đã chọn")
        self.view_button.clicked.connect(self._open_selected_article)

        self.delete_button = QPushButton("Xóa đã chọn")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self._delete_selected_articles)

        bottom_row.addWidget(self.pagination_label)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.prev_page_button)
        bottom_row.addWidget(self.next_page_button)
        bottom_row.addWidget(self.view_button)
        bottom_row.addWidget(self.delete_button)
        layout.addLayout(bottom_row)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Nhật ký ngắn")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(10)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Nhật ký crawl sẽ hiển thị tại đây...")
        layout.addWidget(self.log_output)
        return group

    def _create_info_box(self, title: str, value: str) -> dict:
        frame = QFrame()
        frame.setProperty("role", "card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setProperty("role", "caption")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #5b331b;")
        value_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return {"frame": frame, "value": value_label}

    def _handle_crawl(self) -> None:
        source_name = self.source_select.currentText()
        crawl_type, url = self._get_active_crawl_payload()

        if crawl_type != "menu" and not url:
            message = "Hãy nhập từ khóa để crawl." if crawl_type == "keyword" else "Hãy nhập URL để crawl."
            QMessageBox.warning(self, "Thiếu dữ liệu", message)
            return

        if crawl_type == "menu":
            url = "https://vnexpress.net"

        if source_name != "vnexpress" and self.crawl_comments_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Không hỗ trợ",
                "Nguồn hiện tại chưa hỗ trợ crawl comment.",
            )
            return

        self._append_log(f"Bắt đầu crawl {source_name} | loại {crawl_type} | dữ liệu: {url}")
        self.status_label.setText("Đang khởi động tiến trình crawl...")
        self._set_running_state(True)

        self.worker_thread = QThread(self)
        self.worker = CrawlWorker(
            service=self.service,
            source_name=source_name,
            crawl_type=crawl_type,
            url=url,
            max_pages=self.max_pages_input.value(),
            max_articles=self.max_articles_input.value(),
            crawl_comments=self.crawl_comments_checkbox.isChecked(),
            force_refresh=self.force_refresh_checkbox.isChecked(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._handle_crawl_finished)
        self.worker.failed.connect(self._handle_crawl_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()
        self.progress_timer.start()

    def _handle_stop(self) -> None:
        source_name = self.source_select.currentText()
        self.service.stop_current_crawl(source_name)
        self._append_log("Đã gửi yêu cầu dừng crawl.")
        self.status_label.setText("Đang dừng crawl an toàn...")

    def _handle_crawl_finished(self, result: dict) -> None:
        self._set_running_state(False)
        fetched = result.get("fetched", result.get("total", 0))
        inserted = result.get("inserted", result.get("main_categories", 0))
        skipped = result.get("skipped", result.get("sub_categories", 0))
        self.status_label.setText(
            f"Hoàn tất. Đã lấy {fetched}, thêm mới {inserted}, bỏ qua {skipped}."
        )
        self.progress_bar.setValue(100)
        self._append_log(f"Kết quả: {result}")
        self._load_filter_options()
        self._load_articles(reset_page=False)

    def _handle_crawl_failed(self, error_message: str) -> None:
        self._set_running_state(False)
        self.status_label.setText("Crawl thất bại.")
        self._append_log(f"Lỗi: {error_message}")
        QMessageBox.critical(self, "Lỗi crawl", error_message)

    def _cleanup_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
            self.worker_thread = None

    def _set_running_state(self, is_running: bool) -> None:
        self.crawl_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        self.refresh_button.setEnabled(not is_running)
        self.source_select.setEnabled(not is_running)
        self.control_tabs.setEnabled(not is_running)
        self.url_crawl_type_select.setEnabled(not is_running)
        self.url_input.setEnabled(not is_running and self.url_crawl_type_select.currentText() != "menu")
        self.keyword_crawl_input.setEnabled(not is_running)
        use_vnexpress_options = self.source_select.currentText() == "vnexpress" or self.control_tabs.currentIndex() == 1
        self.max_pages_input.setEnabled(not is_running and use_vnexpress_options)
        self.max_articles_input.setEnabled(not is_running and use_vnexpress_options)
        self.crawl_comments_checkbox.setEnabled(not is_running and use_vnexpress_options)
        self.force_refresh_checkbox.setEnabled(not is_running)
        self.local_search_input.setEnabled(not is_running)
        self.delete_button.setEnabled(not is_running)
        if is_running:
            self.progress_bar.setValue(0)
            self.current_url_value["value"].setText("Đang chuẩn bị...")
            self.article_count_value["value"].setText("0 bài")
            self.error_count_value["value"].setText("0")
        else:
            self.progress_timer.stop()
            self._update_progress_ui()

    def _handle_source_changed(self, source_name: str) -> None:
        is_vnexpress = source_name == "vnexpress"
        if is_vnexpress:
            self.url_input.setText("https://vnexpress.net/thoi-su")
        else:
            self.url_crawl_type_select.setCurrentText("article")
            self.url_input.setText("https://vnexpress.net/thoi-su")
        self._handle_url_crawl_type_changed(self.url_crawl_type_select.currentText())
        self._sync_options_for_active_tab()

    def _handle_url_crawl_type_changed(self, crawl_type: str) -> None:
        is_menu = crawl_type == "menu"
        self.url_input.setEnabled(not is_menu and self.crawl_button.isEnabled())
        self.url_label.setText("URL")
        self.url_input.setPlaceholderText("Nhập URL cần crawl")
        if is_menu:
            self.url_input.setText("https://vnexpress.net")

    def _handle_control_tab_changed(self, _index: int) -> None:
        if self.control_tabs.currentIndex() == 1 and self.source_select.currentText() != "vnexpress":
            self.source_select.setCurrentText("vnexpress")
        self._sync_options_for_active_tab()

    def _sync_options_for_active_tab(self) -> None:
        if not hasattr(self, "crawl_button"):
            return
        is_keyword_tab = self.control_tabs.currentIndex() == 1
        self.url_crawl_type_select.setEnabled(not is_keyword_tab and self.crawl_button.isEnabled())
        self.url_input.setEnabled(
            not is_keyword_tab
            and self.crawl_button.isEnabled()
            and self.url_crawl_type_select.currentText() != "menu"
        )
        self.keyword_crawl_input.setEnabled(is_keyword_tab and self.crawl_button.isEnabled())
        self.source_select.setEnabled(self.crawl_button.isEnabled())

    def _get_active_crawl_payload(self) -> tuple[str, str]:
        if self.control_tabs.currentIndex() == 1:
            return "keyword", self.keyword_crawl_input.text().strip()
        return self.url_crawl_type_select.currentText(), self.url_input.text().strip()

    def _update_progress_ui(self) -> None:
        progress = self.service.get_crawl_progress(self.source_select.currentText())
        if not progress:
            return

        total_pages = int(progress.get("total_pages", 0))
        crawled_pages = int(progress.get("crawled_pages", 0))
        crawled_articles = int(progress.get("crawled_articles", 0))
        failed_articles = int(progress.get("failed_articles", 0))
        current_url = progress.get("current_url", "") or "Chưa có"
        status_text = progress.get("status_text", "")
        last_error = progress.get("last_error", "")
        last_error_type = progress.get("last_error_type", "")
        last_error_url = progress.get("last_error_url", "")
        last_error_title = progress.get("last_error_title", "")
        comment_error = progress.get("comment_error", "")

        if total_pages > 0:
            percent = min(100, int(crawled_pages * 100 / total_pages))
            self.progress_bar.setValue(percent)

        self.current_url_value["value"].setText(current_url)
        self.article_count_value["value"].setText(f"{crawled_articles} bài")
        self.error_count_value["value"].setText(str(failed_articles))
        if status_text:
            self.status_label.setText(status_text)
        else:
            self.status_label.setText(
                f"Đang crawl {crawled_pages}/{total_pages} trang | "
                f"đã xử lý {crawled_articles} bài | lỗi {failed_articles}."
            )

        snapshot = (
            current_url,
            crawled_pages,
            total_pages,
            crawled_articles,
            failed_articles,
            last_error,
            comment_error,
        )
        if snapshot != self._last_progress_snapshot:
            self._append_log(
                f"Đang crawl: {current_url} | "
                f"Trang: {crawled_pages}/{total_pages} | "
                f"Bài: {crawled_articles} | "
                f"Lỗi: {failed_articles}"
            )
            if last_error:
                self._append_log(
                    f"Trace lỗi [{last_error_type or 'unknown'}] | "
                    f"URL: {last_error_url or 'N/A'} | "
                    f"Tiêu đề: {last_error_title or 'N/A'} | "
                    f"Chi tiết: {last_error}"
                )
            elif comment_error:
                self._append_log(
                    f"Trace lỗi [comment] | "
                    f"URL: {last_error_url or current_url or 'N/A'} | "
                    f"Tiêu đề: {last_error_title or 'N/A'} | "
                    f"Chi tiết: {comment_error}"
                )
            self._last_progress_snapshot = snapshot

    def _handle_refresh_all(self) -> None:
        self._load_filter_options()
        self._load_articles()

    def _load_filter_options(self) -> None:
        categories = self.service.list_article_categories()
        current_value = self.category_filter.currentText() if hasattr(self, "category_filter") else ""
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Tất cả chuyên mục")
        self.category_filter.addItems(categories)
        if current_value and self.category_filter.findText(current_value) >= 0:
            self.category_filter.setCurrentText(current_value)
        self.category_filter.blockSignals(False)

    def _apply_filters(self) -> None:
        self.is_local_search_mode = False
        self.current_page = 1
        self._load_articles()

    def _apply_local_search(self) -> None:
        self.is_local_search_mode = True
        self.current_page = 1
        self._load_articles()

    def _handle_page_size_changed(self, value: str) -> None:
        self.page_size = int(value)
        self.current_page = 1
        self._load_articles()

    def _go_prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._load_articles(reset_page=False)

    def _go_next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_articles(reset_page=False)

    def _load_articles(self, reset_page: bool = False) -> None:
        if reset_page:
            self.current_page = 1

        source_value = self.source_filter.currentText()
        source_filter = "" if source_value == "Tất cả nguồn" else source_value
        category_value = self.category_filter.currentText()
        category_filter = "" if category_value == "Tất cả chuyên mục" else category_value

        result = self.service.list_articles_paginated(
            page=self.current_page,
            page_size=self.page_size,
            keyword=self.keyword_input.text().strip(),
            category=category_filter,
            source=source_filter,
        ) if not self.is_local_search_mode else {
            "items": self.service.search_local_articles(
                keyword=self.local_search_input.text().strip(),
                limit=self.page_size,
                offset=(self.current_page - 1) * self.page_size,
            ),
            "page": self.current_page,
            "total_pages": max(
                1,
                math.ceil(
                    self.service.count_local_search_articles(
                        keyword=self.local_search_input.text().strip(),
                    ) / self.page_size
                ),
            ),
            "total_items": self.service.count_local_search_articles(
                keyword=self.local_search_input.text().strip(),
            ),
        }
        self.current_rows = result["items"]
        self.total_pages = result["total_pages"]
        self.current_page = min(result["page"], self.total_pages)

        self.table.setRowCount(len(self.current_rows))
        for row_index, row in enumerate(self.current_rows):
            values = [
                row["id"],
                row["title"],
                row["category"],
                row["published_time_text"] or row["published_at"],
                row["crawled_at"],
                row["source_url"],
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 1:
                    item.setForeground(QColor("#4f2d1b"))
                self.table.setItem(row_index, column_index, item)

        mode_label = "Tìm local" if self.is_local_search_mode else "Danh sách"
        self.pagination_label.setText(
            f"{mode_label} | Trang {self.current_page}/{self.total_pages} | Tổng {result['total_items']} bài"
        )
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)
        self.table.resizeRowsToContents()

    def _show_selected_article(self, row: int, _column: int) -> None:
        self._open_article_by_row(row)

    def _open_selected_article(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn bài", "Hãy chọn một bài trong danh sách.")
            return
        self._open_article_by_row(row)

    def _open_article_by_row(self, row: int) -> None:
        if row < 0 or row >= len(self.current_rows):
            return
        article_id = int(self.current_rows[row]["id"])
        article = self.service.get_article_detail(article_id)
        if article is None:
            QMessageBox.warning(self, "Không tìm thấy", "Không đọc được chi tiết bài viết.")
            return
        dialog = ArticleDetailDialog(article, self)
        dialog.exec()

    def _delete_selected_articles(self) -> None:
        selected_rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not selected_rows:
            QMessageBox.information(self, "Chưa chọn dữ liệu", "Hãy chọn ít nhất một bài để xóa.")
            return

        article_ids = [
            int(self.current_rows[row]["id"])
            for row in selected_rows
            if 0 <= row < len(self.current_rows)
        ]
        if not article_ids:
            QMessageBox.warning(self, "Không hợp lệ", "Không xác định được bài cần xóa.")
            return

        article_count = len(article_ids)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa {article_count} bài đã chọn không?\n"
            "Toàn bộ ảnh và comment liên quan cũng sẽ bị xóa.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        deleted_count = self.service.delete_articles_by_ids(article_ids)
        self._append_log(f"Đã xóa {deleted_count} bài khỏi SQLite.")
        self._load_filter_options()
        self._load_articles(reset_page=False)

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
        scroll_bar = self.log_output.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
