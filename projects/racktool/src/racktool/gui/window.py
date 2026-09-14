from __future__ import annotations

from pathlib import Path
from typing import Any

from racktool.gui.presentation import (
    cell_display_text,
    friendly_conflict_text,
    friendly_exception,
    friendly_status,
)
from racktool.gui.session import GuiSession, default_database_path


def _require_qt() -> tuple[Any, Any, Any]:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as error:
        raise RuntimeError(
            "RackTool GUI requires PySide6. Install it with: pip install 'racktool[gui]'"
        ) from error
    return QtCore, QtGui, QtWidgets


def create_app(argv: list[str] | None = None) -> Any:
    _QtCore, _QtGui, QtWidgets = _require_qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(argv or [])
        app.setApplicationName("RackTool")
        app.setOrganizationName("RackTool")
        app.setStyle("Fusion")
    return app


class CockpitWindow:
    PAGE_OVERVIEW = 0
    PAGE_RACKS = 1
    PAGE_DEVICES = 2
    PAGE_EXCEPTIONS = 3
    DEVICE_PAGE_LIMIT = 100

    def __init__(self) -> None:
        QtCore, QtGui, QtWidgets = _require_qt()
        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.session: GuiSession | None = None
        self._selected_device: str | None = None
        self._selected_rack: str | None = None
        self._rack_scene_device_count = 0

        self.window = QtWidgets.QMainWindow()
        self.window.setObjectName("rackToolWindow")
        self.window.setWindowTitle("RackTool")
        self.window.resize(1440, 900)
        self.window.setMinimumSize(1080, 700)

        root = QtWidgets.QWidget()
        root.setObjectName("root")
        root_layout = QtWidgets.QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.nav_splitter = QtWidgets.QSplitter()
        self.nav_splitter.setObjectName("navSplitter")
        self.nav_splitter.setChildrenCollapsible(False)
        self.nav_splitter.addWidget(self._build_sidebar())
        self.nav_splitter.addWidget(self._build_workspace())
        self.nav_splitter.setStretchFactor(0, 0)
        self.nav_splitter.setStretchFactor(1, 1)
        self.nav_splitter.setHandleWidth(7)
        self.nav_splitter.setSizes([300, 1140])
        self.nav_splitter.splitterMoved.connect(self._resize_rack_items)
        root_layout.addWidget(self.nav_splitter, 1)
        root_layout.addWidget(self._build_move_drawer())
        self.window.setCentralWidget(root)

        self._build_menu()
        self._apply_style()
        self._set_page(self.PAGE_OVERVIEW)
        self.window.statusBar().showMessage("打开工作簿或项目以开始")

    def widget(self) -> Any:
        return self.window

    def load_session(self, session: GuiSession) -> None:
        self.session = session
        self._selected_rack = session.project.racks[0].rack_id if session.project.racks else None
        segments = (
            session.occupancy_segments(self._selected_rack)
            if self._selected_rack is not None
            else []
        )
        self._selected_device = str(segments[0]["device_id"]) if segments else None
        self.move_drawer.hide()
        self._refresh_all()
        self._set_page(self.PAGE_RACKS)

    def _build_sidebar(self) -> Any:
        QtWidgets = self.QtWidgets
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(640)
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 22, 16, 16)
        layout.setSpacing(8)

        brand = QtWidgets.QLabel("▣  RackTool")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        self.project_caption = QtWidgets.QLabel("未打开项目")
        self.project_caption.setObjectName("mutedLabel")
        self.project_caption.setWordWrap(True)
        layout.addWidget(self.project_caption)
        layout.addSpacing(14)

        self.nav_group = QtWidgets.QButtonGroup(sidebar)
        self.nav_group.setExclusive(True)
        nav_items = (
            (self.PAGE_OVERVIEW, "⌂  总览"),
            (self.PAGE_RACKS, "▥  机柜"),
            (self.PAGE_DEVICES, "▦  设备"),
            (self.PAGE_EXCEPTIONS, "△  异常"),
        )
        self.nav_buttons: list[Any] = []
        for page_id, text in nav_items:
            button = QtWidgets.QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(self.QtCore.Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(button, page_id)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        self.nav_group.idClicked.connect(self._set_page)

        layout.addSpacing(14)
        metrics = QtWidgets.QHBoxLayout()
        metrics.setSpacing(7)
        self.rack_metric = self._metric_card("0", "机柜")
        self.device_metric = self._metric_card("0", "设备")
        self.issue_metric = self._metric_card(
            "0",
            "待处理",
            object_name="issueEntryButton",
            clickable=True,
        )
        metrics.addWidget(self.rack_metric)
        metrics.addWidget(self.device_metric)
        metrics.addWidget(self.issue_metric)
        layout.addLayout(metrics)

        self.issue_entry_button = QtWidgets.QPushButton("查看待处理 / 异常")
        self.issue_entry_button.setObjectName("issueEntryLink")
        self.issue_entry_button.setCursor(self.QtCore.Qt.CursorShape.PointingHandCursor)
        self.issue_entry_button.clicked.connect(self._open_exceptions)
        layout.addWidget(self.issue_entry_button)

        rack_heading = QtWidgets.QLabel("机柜列表")
        rack_heading.setObjectName("sectionEyebrow")
        layout.addWidget(rack_heading)
        self.rack_sort_box = QtWidgets.QComboBox()
        self.rack_sort_box.setObjectName("rackSortBox")
        self.rack_sort_box.addItem("按源表位置排序", "source")
        self.rack_sort_box.addItem("按名称排序", "name")
        self.rack_sort_box.addItem("按占用率排序", "occupancy")
        self.rack_sort_box.currentIndexChanged.connect(self._refresh_rack_list)
        layout.addWidget(self.rack_sort_box)
        self.rack_list = QtWidgets.QListWidget()
        self.rack_list.setObjectName("rackList")
        self.rack_list.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.rack_list.setWordWrap(True)
        self.rack_list.setTextElideMode(self.QtCore.Qt.TextElideMode.ElideNone)
        self.rack_list.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.rack_list.currentItemChanged.connect(self._on_rack_item_changed)
        layout.addWidget(self.rack_list, 1)

        self.sidebar = sidebar
        return sidebar

    def _metric_card(
        self,
        value: str,
        caption: str,
        *,
        object_name: str = "metricCard",
        clickable: bool = False,
    ) -> Any:
        QtWidgets = self.QtWidgets
        card = QtWidgets.QPushButton() if clickable else QtWidgets.QFrame()
        card.setObjectName(object_name)
        card.setFixedHeight(72)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(4, 8, 4, 7)
        layout.setSpacing(1)
        number = QtWidgets.QLabel(value)
        number.setObjectName("metricValue")
        number.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignCenter)
        label = QtWidgets.QLabel(caption)
        label.setObjectName("metricLabel")
        label.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(number)
        layout.addWidget(label)
        card.value_label = number
        if clickable:
            card.setCursor(self.QtCore.Qt.CursorShape.PointingHandCursor)
            card.setFocusPolicy(self.QtCore.Qt.FocusPolicy.StrongFocus)
            card.clicked.connect(self._open_exceptions)
            number.setAttribute(self.QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            label.setAttribute(self.QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return card

    def _build_workspace(self) -> Any:
        QtWidgets = self.QtWidgets
        workspace = QtWidgets.QFrame()
        workspace.setObjectName("workspace")
        layout = QtWidgets.QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())

        self.content_splitter = QtWidgets.QSplitter()
        self.content_splitter.setObjectName("contentSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_stack = QtWidgets.QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        self.content_stack.addWidget(self._build_overview_page())
        self.content_stack.addWidget(self._build_rack_page())
        self.content_stack.addWidget(self._build_devices_page())
        self.content_stack.addWidget(self._build_exceptions_page())
        self.content_splitter.addWidget(self.content_stack)
        self.content_splitter.addWidget(self._build_detail_panel())
        self.content_splitter.setStretchFactor(0, 5)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes([770, 320])
        layout.addWidget(self.content_splitter, 1)
        layout.addWidget(self._build_pending_panel())
        return workspace

    def _build_header(self) -> Any:
        QtWidgets = self.QtWidgets
        header = QtWidgets.QFrame()
        header.setObjectName("header")
        header.setFixedHeight(76)
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(24, 14, 18, 14)
        layout.setSpacing(10)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(0)
        title = QtWidgets.QLabel("机柜项目")
        title.setObjectName("headerTitle")
        self.workbook_caption = QtWidgets.QLabel("尚未载入工作簿")
        self.workbook_caption.setObjectName("mutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(self.workbook_caption)
        layout.addLayout(title_box)
        layout.addStretch(1)

        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("搜索设备、机柜或 U 位")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMinimumWidth(270)
        self.search_box.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_box)
        self.open_button = QtWidgets.QPushButton("打开…")
        self.open_button.setObjectName("secondaryButton")
        self.open_button.clicked.connect(self._open_workbook)
        layout.addWidget(self.open_button)
        self.rescan_button = QtWidgets.QPushButton("↻ 重新扫描")
        self.rescan_button.setObjectName("secondaryButton")
        self.rescan_button.clicked.connect(self._rescan)
        layout.addWidget(self.rescan_button)
        self.export_button = QtWidgets.QPushButton("⇩ 导出")
        self.export_button.setObjectName("secondaryButton")
        self.export_button.clicked.connect(self._export_json)
        layout.addWidget(self.export_button)
        self.pending_button = QtWidgets.QPushButton("待同步  0")
        self.pending_button.setObjectName("pendingButton")
        self.pending_button.clicked.connect(self._show_pending_panel)
        layout.addWidget(self.pending_button)
        self.sync_button = QtWidgets.QPushButton("同步更改")
        self.sync_button.setObjectName("globalSyncButton")
        self.sync_button.setAccessibleName("全局同步更改")
        self.sync_button.setEnabled(False)
        self.sync_button.clicked.connect(self._sync_pending)
        layout.addWidget(self.sync_button)
        return header

    def _build_overview_page(self) -> Any:
        QtWidgets = self.QtWidgets
        page = QtWidgets.QWidget()
        page.setObjectName("page")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        title = QtWidgets.QLabel("项目总览")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QtWidgets.QLabel("从一个工作簿查看机柜容量、设备和需要处理的异常。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(14)
        self.overview_racks = self._overview_card("机柜", "0", "已识别")
        self.overview_devices = self._overview_card("设备", "0", "已纳入项目")
        self.overview_occupancy = self._overview_card("总体占用", "0%", "按 U 位计算")
        self.overview_issues = self._overview_card(
            "异常",
            "0",
            "需检查",
            object_name="overviewIssueEntry",
            clickable=True,
        )
        for card in (
            self.overview_racks,
            self.overview_devices,
            self.overview_occupancy,
            self.overview_issues,
        ):
            cards.addWidget(card)
        layout.addLayout(cards)

        sheet_bar = QtWidgets.QHBoxLayout()
        sheet_label = QtWidgets.QLabel("工作表视图")
        sheet_label.setObjectName("panelTitle")
        self.overview_sheet_box = QtWidgets.QComboBox()
        self.overview_sheet_box.setObjectName("overviewSheetBox")
        self.overview_sheet_box.setMinimumWidth(180)
        self.overview_sheet_box.currentIndexChanged.connect(self._render_overview_sheet)
        sheet_hint = QtWidgets.QLabel("按源 Excel 的行列位置查看整体排布，可点击机柜进入详情。")
        sheet_hint.setObjectName("pageSubtitle")
        sheet_bar.addWidget(sheet_label)
        sheet_bar.addWidget(self.overview_sheet_box)
        sheet_bar.addWidget(sheet_hint, 1)
        layout.addLayout(sheet_bar)

        sheet_frame = QtWidgets.QFrame()
        sheet_frame.setObjectName("rackCanvasFrame")
        sheet_layout = QtWidgets.QVBoxLayout(sheet_frame)
        sheet_layout.setContentsMargins(8, 8, 8, 8)
        self.overview_scene = QtWidgets.QGraphicsScene()
        self.overview_view = QtWidgets.QGraphicsView(self.overview_scene)
        self.overview_view.setObjectName("overviewSheetView")
        self.overview_view.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.overview_view.setRenderHint(self.QtGui.QPainter.RenderHint.Antialiasing)
        self.overview_view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.overview_view.setAlignment(
            self.QtCore.Qt.AlignmentFlag.AlignLeft | self.QtCore.Qt.AlignmentFlag.AlignTop
        )
        self.overview_scene.selectionChanged.connect(self._on_overview_selection_changed)
        sheet_layout.addWidget(self.overview_view, 1)
        layout.addWidget(sheet_frame, 1)

        self.overview_status = QtWidgets.QLabel("打开工作簿后，这里会显示项目状态。")
        self.overview_status.setObjectName("pageSubtitle")
        self.overview_status.setWordWrap(True)
        layout.addWidget(self.overview_status)
        return page

    def _overview_card(
        self,
        title: str,
        value: str,
        caption: str,
        *,
        object_name: str = "overviewCard",
        clickable: bool = False,
    ) -> Any:
        QtWidgets = self.QtWidgets
        card = QtWidgets.QPushButton() if clickable else QtWidgets.QFrame()
        card.setObjectName(object_name)
        card.setFixedHeight(96)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        label = QtWidgets.QLabel(title)
        label.setObjectName("mutedLabel")
        number = QtWidgets.QLabel(value)
        number.setObjectName("overviewValue")
        detail = QtWidgets.QLabel(caption)
        detail.setObjectName("metricLabel")
        layout.addWidget(label)
        layout.addWidget(number)
        layout.addWidget(detail)
        card.value_label = number
        if clickable:
            card.setCursor(self.QtCore.Qt.CursorShape.PointingHandCursor)
            card.clicked.connect(self._open_exceptions)
            label.setAttribute(self.QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            number.setAttribute(self.QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            detail.setAttribute(self.QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return card

    def _build_rack_page(self) -> Any:
        QtWidgets = self.QtWidgets
        page = QtWidgets.QWidget()
        page.setObjectName("page")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 22, 20)
        layout.setSpacing(8)
        heading = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        self.rack_title = QtWidgets.QLabel("选择一个机柜")
        self.rack_title.setObjectName("pageTitle")
        self.rack_subtitle = QtWidgets.QLabel("—")
        self.rack_subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(self.rack_title)
        title_box.addWidget(self.rack_subtitle)
        heading.addLayout(title_box)
        heading.addStretch(1)
        self.rack_health = QtWidgets.QLabel("未载入")
        self.rack_health.setObjectName("statusPill")
        heading.addWidget(self.rack_health)
        layout.addLayout(heading)

        rack_frame = QtWidgets.QFrame()
        rack_frame.setObjectName("rackCanvasFrame")
        rack_layout = QtWidgets.QHBoxLayout(rack_frame)
        rack_layout.setContentsMargins(10, 10, 10, 10)
        self.rack_scene = QtWidgets.QGraphicsScene()
        self.rack_scene.selectionChanged.connect(self._on_scene_selection_changed)
        self.rack_view = QtWidgets.QGraphicsView(self.rack_scene)
        self.rack_view.setObjectName("rackView")
        self.rack_view.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.rack_view.setRenderHint(self.QtGui.QPainter.RenderHint.Antialiasing)
        self.rack_view.setAlignment(
            self.QtCore.Qt.AlignmentFlag.AlignHCenter
            | self.QtCore.Qt.AlignmentFlag.AlignTop
        )
        self.rack_view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        rack_layout.addWidget(self.rack_view, 1)
        zoom = QtWidgets.QVBoxLayout()
        zoom.setSpacing(4)
        zoom_in = QtWidgets.QPushButton("+")
        zoom_out = QtWidgets.QPushButton("−")
        fit = QtWidgets.QPushButton("适应")
        for button in (zoom_in, zoom_out, fit):
            button.setObjectName("zoomButton")
            zoom.addWidget(button)
        zoom.addStretch(1)
        zoom_in.clicked.connect(lambda: self.rack_view.scale(1.15, 1.15))
        zoom_out.clicked.connect(lambda: self.rack_view.scale(0.87, 0.87))
        fit.clicked.connect(self._fit_rack_view)
        rack_layout.addLayout(zoom)
        layout.addWidget(rack_frame, 1)
        return page

    def _build_devices_page(self) -> Any:
        QtWidgets = self.QtWidgets
        page = QtWidgets.QWidget()
        page.setObjectName("page")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 22, 20)
        title = QtWidgets.QLabel("设备")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.device_count_label = QtWidgets.QLabel("尚未载入设备")
        self.device_count_label.setObjectName("pageSubtitle")
        layout.addWidget(self.device_count_label)
        filters = QtWidgets.QHBoxLayout()
        filters.setSpacing(8)
        self.device_rack_filter = self._filter_box(
            "deviceRackFilter",
            (("全部机柜", ""),),
        )
        self.device_status_filter = self._filter_box(
            "deviceStatusFilter",
            (
                ("全部状态", "all"),
                ("正常", "active"),
                ("需关注", "attention"),
            ),
        )
        self.device_height_filter = self._filter_box(
            "deviceHeightFilter",
            (
                ("全部高度", "all"),
                ("1U", "1u"),
                ("2–4U", "2-4u"),
                ("5U 及以上", "5u-plus"),
            ),
        )
        self.device_sort_box = self._filter_box(
            "deviceSortBox",
            (
                ("按源表顺序", "source"),
                ("按名称", "name"),
                ("按机柜 / U 位", "rack-u"),
            ),
        )
        for box in (
            self.device_rack_filter,
            self.device_status_filter,
            self.device_height_filter,
            self.device_sort_box,
        ):
            box.currentIndexChanged.connect(self._refresh_device_table)
            filters.addWidget(box)
        filters.addStretch(1)
        layout.addLayout(filters)
        self.device_table = QtWidgets.QTableWidget(0, 5)
        self.device_table.setObjectName("deviceTable")
        self.device_table.setHorizontalHeaderLabels(["设备", "机柜", "U 位", "高度", "状态"])
        self._configure_table(self.device_table, stretch_column=0)
        self.device_table.itemSelectionChanged.connect(self._on_device_table_selected)
        layout.addWidget(self.device_table, 1)
        return page

    def _build_exceptions_page(self) -> Any:
        QtWidgets = self.QtWidgets
        page = QtWidgets.QWidget()
        page.setObjectName("page")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 22, 20)
        title = QtWidgets.QLabel("异常与冲突")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QtWidgets.QLabel(
            "同类问题会合并显示。需要处理的项目会阻止同步；提醒不会。"
            "请先在 Excel 中修正后保存，再重新扫描。"
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        action_row = QtWidgets.QHBoxLayout()
        self.exception_rescan_button = QtWidgets.QPushButton("修正 Excel 后重新扫描")
        self.exception_rescan_button.setObjectName("primaryButton")
        self.exception_rescan_button.clicked.connect(self._rescan)
        self.exception_help = QtWidgets.QLabel(
            "原始代码和英文仅作为次级技术详情，不作为操作说明。"
        )
        self.exception_help.setObjectName("pageSubtitle")
        self.exception_help.setWordWrap(True)
        action_row.addWidget(self.exception_rescan_button)
        action_row.addWidget(self.exception_help, 1)
        layout.addLayout(action_row)
        self.exception_table = QtWidgets.QTableWidget(0, 3)
        self.exception_table.setObjectName("exceptionTable")
        self.exception_table.setHorizontalHeaderLabels(["级别", "问题", "如何处理"])
        self._configure_table(self.exception_table, stretch_column=2)
        self.exception_table.itemSelectionChanged.connect(self._on_exception_selected)
        layout.addWidget(self.exception_table, 1)
        self.exception_technical_toggle = QtWidgets.QPushButton("›  技术详情")
        self.exception_technical_toggle.setObjectName("disclosureButton")
        self.exception_technical_toggle.setCheckable(True)
        self.exception_technical_toggle.toggled.connect(self._toggle_exception_technical)
        layout.addWidget(self.exception_technical_toggle)
        self.exception_technical = QtWidgets.QPlainTextEdit()
        self.exception_technical.setObjectName("exceptionTechnicalDetail")
        self.exception_technical.setReadOnly(True)
        self.exception_technical.setMaximumHeight(110)
        self.exception_technical.hide()
        layout.addWidget(self.exception_technical)
        return page

    def _filter_box(self, object_name: str, items: tuple[tuple[str, str], ...]) -> Any:
        box = self.QtWidgets.QComboBox()
        box.setObjectName(object_name)
        for label, value in items:
            box.addItem(label, value)
        return box

    def _configure_table(self, table: Any, *, stretch_column: int | None = None) -> None:
        QtWidgets = self.QtWidgets
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().hide()
        table.setWordWrap(True)
        table.setTextElideMode(self.QtCore.Qt.TextElideMode.ElideNone)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        stretch = table.columnCount() - 1 if stretch_column is None else stretch_column
        table.horizontalHeader().setSectionResizeMode(
            stretch,
            QtWidgets.QHeaderView.ResizeMode.Stretch,
        )

    def _build_detail_panel(self) -> Any:
        QtWidgets = self.QtWidgets
        panel = QtWidgets.QFrame()
        panel.setObjectName("detailPanel")
        panel.setMinimumWidth(285)
        panel.setMaximumWidth(390)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(20, 22, 20, 18)
        layout.setSpacing(12)
        title = QtWidgets.QLabel("设备详情")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        self.device_name = QtWidgets.QLabel("请选择设备")
        self.device_name.setObjectName("deviceName")
        self.device_name.setWordWrap(True)
        self.device_name.setTextInteractionFlags(
            self.QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.device_name)
        self.device_status = QtWidgets.QLabel("—")
        self.device_status.setObjectName("statusPill")
        layout.addWidget(self.device_status, 0, self.QtCore.Qt.AlignmentFlag.AlignLeft)

        info = QtWidgets.QFrame()
        info.setObjectName("softPanel")
        info_layout = QtWidgets.QGridLayout(info)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setHorizontalSpacing(14)
        info_layout.setVerticalSpacing(10)
        self.detail_rack = self._detail_row(info_layout, 0, "所在机柜")
        self.detail_u = self._detail_row(info_layout, 1, "U 位")
        self.detail_height = self._detail_row(info_layout, 2, "高度")
        self.detail_sheet = self._detail_row(info_layout, 3, "来源 Sheet")
        layout.addWidget(info)
        self.move_button = QtWidgets.QPushButton("移动设备")
        self.move_button.setObjectName("primaryButton")
        self.move_button.setEnabled(False)
        self.move_button.clicked.connect(self._open_move_drawer)
        layout.addWidget(self.move_button)
        self.technical_toggle = QtWidgets.QPushButton("›  技术信息")
        self.technical_toggle.setObjectName("disclosureButton")
        self.technical_toggle.setCheckable(True)
        self.technical_toggle.toggled.connect(self._toggle_technical)
        layout.addWidget(self.technical_toggle)
        self.technical_panel = QtWidgets.QFrame()
        self.technical_panel.setObjectName("softPanel")
        technical_layout = QtWidgets.QVBoxLayout(self.technical_panel)
        self.technical_id = QtWidgets.QLabel("设备 ID：—")
        self.technical_mapping = QtWidgets.QLabel("来源范围：—")
        for label in (self.technical_id, self.technical_mapping):
            label.setObjectName("technicalText")
            label.setTextInteractionFlags(
                self.QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            label.setWordWrap(True)
            technical_layout.addWidget(label)
        self.technical_panel.hide()
        layout.addWidget(self.technical_panel)
        layout.addStretch(1)
        self.detail_panel = panel
        return panel

    def _detail_row(self, layout: Any, row: int, label: str) -> Any:
        key = self.QtWidgets.QLabel(label)
        key.setObjectName("detailKey")
        value = self.QtWidgets.QLabel("—")
        value.setObjectName("detailValue")
        value.setWordWrap(True)
        layout.addWidget(key, row, 0)
        layout.addWidget(value, row, 1)
        return value

    def _build_pending_panel(self) -> Any:
        QtWidgets = self.QtWidgets
        panel = QtWidgets.QFrame()
        panel.setObjectName("pendingPanel")
        panel.setMinimumHeight(128)
        panel.setMaximumHeight(230)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(18, 10, 18, 12)
        layout.setSpacing(6)
        header = QtWidgets.QHBoxLayout()
        self.pending_title = QtWidgets.QLabel("待同步的更改 (0)")
        self.pending_title.setObjectName("panelTitle")
        self.clear_pending_button = QtWidgets.QPushButton("清空")
        self.clear_pending_button.setObjectName("dangerLink")
        self.clear_pending_button.clicked.connect(self._clear_pending)
        header.addWidget(self.pending_title)
        header.addStretch(1)
        header.addWidget(self.clear_pending_button)
        layout.addLayout(header)
        self.pending_table = QtWidgets.QTableWidget(0, 4)
        self.pending_table.setObjectName("pendingTable")
        self.pending_table.setHorizontalHeaderLabels(["设备", "当前位置", "目标位置", "操作"])
        self._configure_table(self.pending_table, stretch_column=0)
        self.pending_table.setMaximumHeight(150)
        layout.addWidget(self.pending_table)
        self.pending_panel = panel
        return panel

    def _build_move_drawer(self) -> Any:
        QtWidgets = self.QtWidgets
        drawer = QtWidgets.QFrame()
        drawer.setObjectName("moveDrawer")
        drawer.setFixedWidth(390)
        drawer.hide()
        layout = QtWidgets.QVBoxLayout(drawer)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("移动设备")
        title.setObjectName("drawerTitle")
        close_button = QtWidgets.QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self._cancel_move_drawer)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close_button)
        layout.addLayout(header)
        self.drawer_device_name = QtWidgets.QLabel("—")
        self.drawer_device_name.setObjectName("deviceName")
        self.drawer_device_name.setWordWrap(True)
        layout.addWidget(self.drawer_device_name)

        step_one = QtWidgets.QLabel("1   选择目标位置")
        step_one.setObjectName("stepTitle")
        layout.addWidget(step_one)
        layout.addWidget(self._field_label("目标机柜"))
        self.target_rack_box = QtWidgets.QComboBox()
        self.target_rack_box.setObjectName("fieldControl")
        self.target_rack_box.currentIndexChanged.connect(self._schedule_move_preview)
        layout.addWidget(self.target_rack_box)
        layout.addWidget(self._field_label("目标起始 U 位"))
        self.target_start_u = QtWidgets.QSpinBox()
        self.target_start_u.setObjectName("fieldControl")
        self.target_start_u.setRange(1, 100)
        self.target_start_u.valueChanged.connect(self._schedule_move_preview)
        layout.addWidget(self.target_start_u)
        self.target_range_label = QtWidgets.QLabel("目标范围：—")
        self.target_range_label.setObjectName("pageSubtitle")
        layout.addWidget(self.target_range_label)

        step_two = QtWidgets.QLabel("2   冲突检查")
        step_two.setObjectName("stepTitle")
        layout.addWidget(step_two)
        self.preview_box = QtWidgets.QFrame()
        self.preview_box.setObjectName("previewNeutral")
        preview_layout = QtWidgets.QVBoxLayout(self.preview_box)
        self.preview_title = QtWidgets.QLabel("等待选择位置")
        self.preview_title.setObjectName("previewTitle")
        self.preview_message = QtWidgets.QLabel("选择目标机柜和 U 位后自动检查。")
        self.preview_message.setObjectName("previewMessage")
        self.preview_message.setWordWrap(True)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_message)
        layout.addWidget(self.preview_box)
        note = QtWidgets.QLabel(
            "此操作只会加入待同步列表，不会立即写入工作簿。"
            "确认所有更改后，使用窗口顶部的“同步更改”。"
        )
        note.setObjectName("infoNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        buttons = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("取消")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self._cancel_move_drawer)
        self.drawer_add_button = QtWidgets.QPushButton("加入待同步")
        self.drawer_add_button.setObjectName("primaryButton")
        self.drawer_add_button.setEnabled(False)
        self.drawer_add_button.clicked.connect(self._stage_drawer_move)
        buttons.addWidget(cancel)
        buttons.addWidget(self.drawer_add_button, 1)
        layout.addLayout(buttons)
        self.preview_timer = self.QtCore.QTimer(drawer)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(180)
        self.preview_timer.timeout.connect(self._update_move_preview)
        self.move_drawer = drawer
        return drawer

    def _field_label(self, text: str) -> Any:
        label = self.QtWidgets.QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _build_menu(self) -> None:
        file_menu = self.window.menuBar().addMenu("文件")
        open_workbook = file_menu.addAction("打开工作簿…", self._open_workbook)
        open_workbook.setShortcut("Ctrl+O")
        file_menu.addAction("打开项目…", self._open_project)
        file_menu.addSeparator()
        file_menu.addAction("重新扫描", self._rescan)
        file_menu.addAction("导出 JSON…", self._export_json)
        file_menu.addAction("恢复备份…", self._restore_backup)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.window.close)

    def _apply_style(self) -> None:
        self.window.setStyleSheet(
            """
            * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
            QMainWindow, #root, #workspace, #page { background: #f7f9fc; color: #172033; }
            QMenuBar { background: #ffffff; border-bottom: 1px solid #e8edf4; }
            QStatusBar { background: #ffffff; color: #667085; border-top: 1px solid #e6eaf0; }
            #sidebar { background: #f1f5fa; border-right: 1px solid #dfe6ef; }
            #brand { font-size: 22px; font-weight: 750; color: #111827; padding: 2px 2px 6px; }
            #mutedLabel, #pageSubtitle, #metricLabel { color: #667085; font-size: 12px; }
            #navButton { text-align: left; border: 0; border-radius: 9px; padding: 11px 13px;
                         color: #344054; font-size: 14px; background: transparent; }
            #navButton:hover { background: #e8eef7; }
            #navButton:checked { background: #dcecff; color: #0866d9; font-weight: 700; }
            #metricCard, #overviewCard, #panel { background: #ffffff; border: 1px solid #e1e7ef;
                                               border-radius: 10px; }
            #issueEntryButton, #overviewIssueEntry { background: #ffffff; border: 1px solid #e1e7ef;
                                                    border-radius: 10px; }
            #overviewIssueEntry { min-height: 94px; max-height: 94px; }
            #issueEntryButton:hover, #overviewIssueEntry:hover { border: 1px solid #1677ff;
                                                                background: #f4f8ff; }
            #issueEntryLink { text-align: left; background: #eef5ff; border: 1px solid #cfe0fb;
                              border-radius: 8px; padding: 8px 10px; color: #0b63ce; font-weight: 700; }
            #issueEntryLink:hover { background: #dcecff; }
            #rackSortBox, #overviewSheetBox, #deviceRackFilter, #deviceStatusFilter,
            #deviceHeightFilter, #deviceSortBox { background: #ffffff; border: 1px solid #d6dee9;
                                                 border-radius: 8px; padding: 4px 8px; min-height: 28px; }
            #overviewSheetView { background: #ffffff; }
            #metricValue { font-size: 18px; font-weight: 750; color: #172033; }
            #overviewValue { font-size: 28px; font-weight: 750; color: #172033; }
            #sectionEyebrow { font-size: 12px; font-weight: 700; color: #667085; padding: 8px 3px 2px; }
            #rackList { background: transparent; outline: none; }
            #rackList::item { padding: 10px 10px; margin: 1px 0; border-radius: 8px; color: #344054; }
            #rackList::item:selected { background: #dcecff; color: #0b63ce; }
            #header { background: #ffffff; border-bottom: 1px solid #e1e7ef; }
            #headerTitle { font-size: 17px; font-weight: 750; color: #172033; }
            #searchBox, #fieldControl { background: #f8fafc; border: 1px solid #d6dee9;
                                        border-radius: 8px; padding: 8px 11px; min-height: 20px; }
            #searchBox:focus, #fieldControl:focus { border: 1px solid #1677ff; background: #ffffff; }
            QPushButton { min-height: 20px; }
            #secondaryButton { background: #ffffff; border: 1px solid #d6dee9; border-radius: 8px;
                               padding: 8px 13px; color: #344054; font-weight: 600; }
            #secondaryButton:hover { background: #f3f6fa; }
            #pendingButton { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px;
                             padding: 8px 13px; color: #b45309; font-weight: 700; }
            #globalSyncButton, #primaryButton { background: #0b6df6; border: 1px solid #0b6df6;
                                               border-radius: 8px; padding: 9px 16px;
                                               color: #ffffff; font-weight: 700; }
            #globalSyncButton:hover, #primaryButton:hover { background: #075fd8; }
            #globalSyncButton:disabled, #primaryButton:disabled { background: #a9c8f7;
                                                                  border-color: #a9c8f7; }
            #pageTitle { font-size: 25px; font-weight: 760; color: #111827; }
            #panelTitle { font-size: 15px; font-weight: 750; color: #172033; }
            #emptyState { color: #667085; font-size: 14px; padding: 20px; }
            #rackCanvasFrame { background: #ffffff; border: 1px solid #e1e7ef; border-radius: 12px; }
            #rackView { background: #ffffff; }
            #zoomButton { background: #ffffff; border: 1px solid #d6dee9; border-radius: 7px;
                          padding: 5px 7px; min-width: 38px; }
            #statusPill { background: #dcfce7; color: #16803d; border-radius: 10px;
                          padding: 4px 9px; font-weight: 700; }
            #detailPanel, #moveDrawer { background: #ffffff; border-left: 1px solid #e1e7ef; }
            #deviceName { font-size: 17px; font-weight: 750; color: #172033; padding: 4px 0; }
            #softPanel { background: #f5f7fa; border: 0; border-radius: 9px; }
            #detailKey { color: #667085; font-size: 12px; }
            #detailValue { color: #172033; font-weight: 650; }
            #disclosureButton { text-align: left; background: #f5f7fa; border: 0;
                                border-radius: 8px; padding: 9px; color: #344054; }
            #technicalText { color: #667085; font-family: Menlo, monospace; font-size: 10px; }
            #pendingPanel { background: #ffffff; border-top: 1px solid #e1e7ef; }
            #dangerLink { background: transparent; border: 0; color: #d92d20; font-weight: 600; }
            QTableWidget { background: #ffffff; alternate-background-color: #fafbfc;
                           border: 1px solid #e1e7ef; border-radius: 8px; gridline-color: #eef1f5;
                           selection-background-color: #dcecff; selection-color: #172033; }
            QHeaderView::section { background: #f5f7fa; color: #667085; padding: 8px;
                                   border: 0; border-bottom: 1px solid #e1e7ef; font-weight: 700; }
            #drawerTitle { font-size: 22px; font-weight: 760; color: #111827; }
            #closeButton { border: 0; background: transparent; font-size: 24px; color: #667085; }
            #stepTitle { font-size: 14px; font-weight: 750; color: #172033; padding-top: 6px; }
            #fieldLabel { font-size: 12px; color: #667085; }
            #previewNeutral, #previewSuccess, #previewError { border-radius: 9px; }
            #previewNeutral { background: #f5f7fa; border: 1px solid #e1e7ef; }
            #previewSuccess { background: #edfcf2; border: 1px solid #a6e7bb; }
            #previewError { background: #fff1f0; border: 1px solid #f5b7b1; }
            #previewTitle { font-weight: 750; color: #172033; }
            #previewMessage { color: #667085; font-size: 12px; }
            #infoNote { background: #f0f6ff; color: #365d8d; border-radius: 8px;
                        padding: 11px; font-size: 12px; }
            QSplitter::handle { background: #dfe6ef; }
            QSplitter::handle:hover { background: #98a6b8; }
            QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
            QScrollBar::handle:vertical { background: #c5ceda; border-radius: 4px; min-height: 28px; }
            QScrollBar::handle:vertical:hover { background: #98a6b8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """
        )

    def _set_page(self, page_id: int) -> None:
        if page_id < 0 or page_id >= self.content_stack.count():
            return
        self.content_stack.setCurrentIndex(page_id)
        button = self.nav_group.button(page_id)
        if button is not None:
            button.setChecked(True)
        self.detail_panel.setVisible(page_id in {self.PAGE_RACKS, self.PAGE_DEVICES})
        if page_id == self.PAGE_RACKS:
            self.QtCore.QTimer.singleShot(0, self._fit_rack_view)
        if page_id == self.PAGE_OVERVIEW:
            self.QtCore.QTimer.singleShot(0, self._fit_overview_view)

    def _refresh_all(self) -> None:
        if self.session is None:
            return
        session = self.session
        self.project_caption.setText(session.workbook_path.name)
        self.workbook_caption.setText(session.workbook_path.name)
        self.window.setWindowTitle(f"RackTool — {session.workbook_path.name}")
        self._refresh_metrics()
        self._refresh_rack_list()
        self._refresh_device_table()
        self._refresh_exceptions()
        self._refresh_pending()
        self._render_selected_rack()
        self._refresh_device_detail()
        self.overview_status.setText(
            f"{session.status_message}\n\n源工作簿：{session.workbook_path.name}\n"
            "设备移动会先进入待同步列表，只有顶部“同步更改”会提交。"
        )
        self._refresh_overview_sheet_names()
        self.window.statusBar().showMessage(session.status_message)

    def _refresh_metrics(self) -> None:
        if self.session is None:
            return
        racks = self.session.rack_rows()
        devices = self.session.device_rows()
        issues = self.session.issue_rows()
        occupied = sum(int(row["occupied_u"]) for row in racks)
        capacity = sum(int(row["height_u"]) for row in racks)
        percent = round(occupied / capacity * 100) if capacity else 0
        self.rack_metric.value_label.setText(str(len(racks)))
        self.device_metric.value_label.setText(str(len(devices)))
        issue_count = sum(int(row["count"]) for row in issues)
        self.issue_metric.value_label.setText(str(issue_count))
        self.issue_metric.setAccessibleName(f"待处理：{issue_count}，点击查看异常")
        self.overview_racks.value_label.setText(str(len(racks)))
        self.overview_devices.value_label.setText(str(len(devices)))
        self.overview_occupancy.value_label.setText(f"{percent}%")
        self.overview_issues.value_label.setText(str(issue_count))
        self.overview_issues.setAccessibleName(f"异常：{issue_count}，点击查看处理方法")
        self.issue_entry_button.setText(
            "查看待处理 / 异常" if issue_count == 0 else f"查看待处理 / 异常（{issue_count}）"
        )

    def _refresh_rack_list(self) -> None:
        if self.session is None:
            return
        query = self.search_box.text().strip().casefold()
        matching_racks = {
            str(row["rack_id"])
            for row in self.session.device_rows()
            if query and query in str(row["display_text"]).casefold()
        }
        self.rack_list.blockSignals(True)
        self.rack_list.clear()
        selected_item = None
        sort_by = str(self.rack_sort_box.currentData() or "source")
        for row in self.session.rack_rows(sort_by=sort_by):
            rack_id = str(row["rack_id"])
            rack_name = str(row["rack_name"])
            if query and query not in rack_name.casefold() and rack_id not in matching_racks:
                continue
            marker = "●" if row["status"] == "active" else "○"
            text = f"{marker}  {rack_name}"
            item = self.QtWidgets.QListWidgetItem(text)
            item.setData(self.QtCore.Qt.ItemDataRole.UserRole, rack_id)
            item.setToolTip(
                f"{rack_name}\n{row['sheet_name'] or '未标注工作表'} · "
                f"{row['device_count']} 台设备，剩余 {row['available_u']}U"
            )
            item.setSizeHint(self._rack_item_size(text))
            self.rack_list.addItem(item)
            if rack_id == self._selected_rack:
                selected_item = item
        self.rack_list.blockSignals(False)
        if selected_item is not None:
            self.rack_list.setCurrentItem(selected_item)
        elif self.rack_list.count():
            self.rack_list.setCurrentRow(0)
            item = self.rack_list.currentItem()
            self._selected_rack = (
                str(item.data(self.QtCore.Qt.ItemDataRole.UserRole)) if item else None
            )

    def _rack_item_size(self, text: str) -> Any:
        lines = text.splitlines() or [""]
        metrics = self.rack_list.fontMetrics()
        content_width = max(metrics.horizontalAdvance(line) for line in lines) + 28
        visible_width = max(self.sidebar.width() - 36, self.sidebar.minimumWidth() - 36, 160)
        height = max(48, metrics.lineSpacing() * len(lines) + 16)
        return self.QtCore.QSize(max(content_width, visible_width), height)

    def _resize_rack_items(self, *_args: Any) -> None:
        for index in range(self.rack_list.count()):
            item = self.rack_list.item(index)
            item.setSizeHint(self._rack_item_size(item.text()))

    def _refresh_device_table(self) -> None:
        if self.session is None:
            self.device_table.setRowCount(0)
            return
        self._refresh_device_filter_options()
        rack_id = self.device_rack_filter.currentData()
        rows, total = self.session.device_page(
            self.search_box.text(),
            rack_id=str(rack_id) if rack_id else None,
            status_filter=str(self.device_status_filter.currentData() or "all"),
            height_filter=str(self.device_height_filter.currentData() or "all"),
            sort_by=str(self.device_sort_box.currentData() or "source"),
            limit=self.DEVICE_PAGE_LIMIT,
        )
        self.device_table.blockSignals(True)
        self.device_table.setRowCount(len(rows))
        selected_row = -1
        for row_index, row in enumerate(rows):
            position = "—"
            if row["start_u"] is not None and row["end_u"] is not None:
                position = (
                    f"U{min(row['start_u'], row['end_u'])}–"
                    f"U{max(row['start_u'], row['end_u'])}"
                )
            values = [
                cell_display_text(str(row["display_text"] or row["primary_label"])),
                str(row["rack_name"] or "未放置"),
                position,
                "—" if row["height_u"] is None else f"{row['height_u']}U",
                friendly_status(str(row["status"])),
            ]
            for column, value in enumerate(values):
                item = self.QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(
                    self.QtCore.Qt.AlignmentFlag.AlignTop | self.QtCore.Qt.AlignmentFlag.AlignLeft
                )
                if column == 0:
                    item.setData(
                        self.QtCore.Qt.ItemDataRole.UserRole,
                        str(row["device_id"]),
                    )
                self.device_table.setItem(row_index, column, item)
            if row["device_id"] == self._selected_device:
                selected_row = row_index
        self.device_table.blockSignals(False)
        if selected_row >= 0:
            self.device_table.selectRow(selected_row)
        self.device_table.resizeRowsToContents()
        shown = len(rows)
        suffix = "" if total <= shown else f"（为保持流畅，仅显示前 {shown} 条）"
        self.device_count_label.setText(f"找到 {total} 台设备{suffix}")

    def _refresh_exceptions(self) -> None:
        if self.session is None:
            return
        rows = self.session.issue_rows()[: self.DEVICE_PAGE_LIMIT]
        self.exception_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["level"]),
                str(row["title"]),
                str(row["guidance"]),
            ]
            for column, value in enumerate(values):
                item = self.QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(
                    self.QtCore.Qt.AlignmentFlag.AlignTop | self.QtCore.Qt.AlignmentFlag.AlignLeft
                )
                if column == 0:
                    item.setData(
                        self.QtCore.Qt.ItemDataRole.UserRole,
                        str(row["technical_detail"]),
                    )
                self.exception_table.setItem(row_index, column, item)
        self.exception_table.resizeRowsToContents()
        if rows:
            self.exception_table.selectRow(0)
            self._on_exception_selected()
        else:
            self.exception_technical.setPlainText("当前没有需要处理的异常。")

    def _refresh_pending(self) -> None:
        rows = self.session.pending_rows() if self.session is not None else []
        count = len(rows)
        self.pending_title.setText(f"待同步的更改 ({count})")
        self.pending_button.setText(f"待同步  {count}")
        self.sync_button.setEnabled(count > 0)
        self.clear_pending_button.setEnabled(count > 0)
        self.clear_pending_button.setVisible(count > 0)
        self.pending_table.setVisible(count > 0)
        self.pending_panel.setFixedHeight(174 if count else 48)
        self.pending_table.setRowCount(count)
        for row_index, row in enumerate(rows):
            source_u = self._format_u_range(
                row.get("source_start_u"),
                row.get("source_end_u"),
            )
            target_u = self._format_u_range(
                row.get("target_start_u"),
                row.get("target_end_u"),
            )
            values = [
                cell_display_text(str(row["display_text"] or row["primary_label"])),
                f"{row['source_rack_name']}  {source_u}",
                f"{row['target_rack_name']}  {target_u}",
            ]
            for column, value in enumerate(values):
                item = self.QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(
                    self.QtCore.Qt.AlignmentFlag.AlignTop | self.QtCore.Qt.AlignmentFlag.AlignLeft
                )
                if column == 0:
                    item.setData(
                        self.QtCore.Qt.ItemDataRole.UserRole,
                        str(row["device_id"]),
                    )
                self.pending_table.setItem(row_index, column, item)
            remove = self.QtWidgets.QPushButton("移除")
            remove.setObjectName("dangerLink")
            remove.clicked.connect(
                lambda _checked=False, device_id=str(row["device_id"]): self._remove_pending(
                    device_id
                )
            )
            self.pending_table.setCellWidget(row_index, 3, remove)

        self.pending_table.resizeRowsToContents()

    def _render_selected_rack(self) -> None:
        self.rack_scene.clear()
        self._rack_scene_device_count = 0
        if self.session is None or self._selected_rack is None:
            self.rack_title.setText("选择一个机柜")
            self.rack_subtitle.setText("—")
            return
        rack = next(
            (
                row
                for row in self.session.rack_rows()
                if row["rack_id"] == self._selected_rack
            ),
            None,
        )
        if rack is None:
            return
        height_u = int(rack["height_u"])
        segments = self.session.occupancy_segments(self._selected_rack)
        per_u_lines = 1.0
        for segment in segments:
            lines = cell_display_text(str(segment["display_text"])).count("\n") + 1
            per_u_lines = max(per_u_lines, lines / max(int(segment["height_u"]), 1))
        unit_height = max(20.0, min(52.0, 16.0 * per_u_lines + 6.0))
        left = 56.0
        top = 24.0
        width = 380.0
        rack_height = height_u * unit_height
        dark_pen = self.QtGui.QPen(self.QtGui.QColor("#27364a"), 3)
        line_pen = self.QtGui.QPen(self.QtGui.QColor("#d5dce6"), 1)
        self.rack_scene.addRect(left, top, width, rack_height, dark_pen)
        for unit in range(height_u, 0, -1):
            y = top + (height_u - unit) * unit_height
            self.rack_scene.addLine(left, y, left + width, y, line_pen)
            label = self.rack_scene.addText(str(unit))
            label.setDefaultTextColor(self.QtGui.QColor("#667085"))
            label.setPos(left - 34, y - 7)
            label.setScale(0.75)
        self.rack_scene.addLine(
            left,
            top + rack_height,
            left + width,
            top + rack_height,
            line_pen,
        )

        palette = (
            ("#dbeafe", "#3b82f6"),
            ("#dcfce7", "#22c55e"),
            ("#f3e8ff", "#8b5cf6"),
            ("#ffe4e6", "#f43f5e"),
            ("#ffedd5", "#f97316"),
            ("#cffafe", "#06b6d4"),
        )
        for segment in segments:
            device_id = str(segment["device_id"])
            index = sum(device_id.encode("utf-8")) % len(palette)
            fill_color, border_color = palette[index]
            end_u = int(segment["end_u"])
            segment_height = int(segment["height_u"]) * unit_height
            y = top + (height_u - end_u) * unit_height
            rect = self.rack_scene.addRect(
                left + 4,
                y + 2,
                width - 8,
                max(segment_height - 4, 12),
                self.QtGui.QPen(self.QtGui.QColor(border_color), 1.5),
                self.QtGui.QBrush(self.QtGui.QColor(fill_color)),
            )
            rect.setData(0, device_id)
            rect.setFlag(
                self.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                True,
            )
            if device_id == self._selected_device:
                rect.setSelected(True)
            device_text = cell_display_text(str(segment["display_text"]))
            text = self.rack_scene.addText("")
            text.setPlainText(device_text)
            font = text.font()
            font.setPointSizeF(9.5)
            text.setFont(font)
            text.setDefaultTextColor(self.QtGui.QColor("#17335f"))
            text.document().setDocumentMargin(1)
            text.setTextWidth(width - 30)
            text.setPos(left + 16, y + 4)
            text.setToolTip(device_text)
            text.setAcceptedMouseButtons(self.QtCore.Qt.MouseButton.NoButton)
            self._rack_scene_device_count += 1

        self.rack_scene.setSceneRect(0, 0, width + 105, rack_height + 48)
        self.rack_title.setText(str(rack["rack_name"]))
        self.rack_subtitle.setText(
            f"{height_u}U · 已使用 {rack['occupied_u']}U "
            f"({rack['occupancy_percent']}%) · 剩余 {rack['available_u']}U"
        )
        self.rack_health.setText("正常" if rack["status"] == "active" else "需检查")
        self.QtCore.QTimer.singleShot(0, self._fit_rack_view)

    def _fit_rack_view(self) -> None:
        if self.rack_scene.items():
            self.rack_view.resetTransform()
            scene_size = self.rack_scene.sceneRect().size()
            viewport_size = self.rack_view.viewport().size()
            if scene_size.width() <= 0 or scene_size.height() <= 0:
                return
            ratio = min(
                1.0,
                viewport_size.width() / scene_size.width(),
                viewport_size.height() / scene_size.height(),
            )
            readable_ratio = max(ratio, 0.82)
            self.rack_view.scale(readable_ratio, readable_ratio)

    def _refresh_device_detail(self) -> None:
        row = self._device_row(self._selected_device)
        if row is None:
            self.device_name.setText("请选择设备")
            self.device_status.setText("—")
            for label in (
                self.detail_rack,
                self.detail_u,
                self.detail_height,
                self.detail_sheet,
            ):
                label.setText("—")
            self.technical_id.setText("设备 ID：—")
            self.technical_mapping.setText("来源范围：—")
            self.device_status.hide()
            self.move_button.setEnabled(False)
            return
        self.device_name.setText(
            cell_display_text(str(row["display_text"] or row["primary_label"]))
        )
        self.device_status.setText(friendly_status(str(row["status"])))
        self.device_status.show()
        self.detail_rack.setText(str(row["rack_name"] or "未放置"))
        self.detail_u.setText(self._format_u_range(row["start_u"], row["end_u"]))
        self.detail_height.setText(
            "—" if row["height_u"] is None else f"{row['height_u']}U"
        )
        self.detail_sheet.setText(str(row["sheet_name"] or "—"))
        self.technical_id.setText(f"设备 ID：{row['device_id']}")
        self.technical_mapping.setText(f"来源范围：{row['source_range'] or '—'}")
        self.move_button.setEnabled(row["status"] == "active")

    def _device_row(self, device_id: str | None) -> dict[str, Any] | None:
        if self.session is None or device_id is None:
            return None
        return next(
            (row for row in self.session.device_rows() if row["device_id"] == device_id),
            None,
        )

    def _on_rack_item_changed(self, current: Any, _previous: Any) -> None:
        if current is None:
            return
        rack_id = str(current.data(self.QtCore.Qt.ItemDataRole.UserRole))
        if rack_id != self._selected_rack:
            self._selected_device = None
        self._selected_rack = rack_id
        self._render_selected_rack()
        self._refresh_device_detail()

    def _on_scene_selection_changed(self) -> None:
        try:
            selected = self.rack_scene.selectedItems()
        except RuntimeError:
            return
        if not selected:
            return
        device_id = selected[0].data(0)
        if device_id:
            self._selected_device = str(device_id)
            self._refresh_device_detail()

    def _on_device_table_selected(self) -> None:
        row_index = self.device_table.currentRow()
        if row_index < 0:
            return
        item = self.device_table.item(row_index, 0)
        if item is None:
            return
        device_id = item.data(self.QtCore.Qt.ItemDataRole.UserRole)
        if not device_id:
            return
        self._selected_device = str(device_id)
        row = self._device_row(self._selected_device)
        if row is not None and row["rack_id"]:
            self._selected_rack = str(row["rack_id"])
        self._refresh_device_detail()

    def _on_search_changed(self, _text: str) -> None:
        if self.session is None:
            return
        self._refresh_rack_list()
        self._refresh_device_table()

    def _toggle_technical(self, expanded: bool) -> None:
        self.technical_panel.setVisible(expanded)
        self.technical_toggle.setText("⌄  技术信息" if expanded else "›  技术信息")

    def _open_move_drawer(self) -> None:
        if self.session is None:
            return
        row = self._device_row(self._selected_device)
        if row is None or row["height_u"] is None:
            return
        self.drawer_device_name.setText(
            cell_display_text(str(row["display_text"] or row["primary_label"]))
        )
        self.target_rack_box.blockSignals(True)
        self.target_rack_box.clear()
        for rack in self.session.rack_rows():
            if rack["status"] != "active":
                continue
            self.target_rack_box.addItem(str(rack["rack_name"]), str(rack["rack_id"]))
        actual_index = self.target_rack_box.findData(str(row["rack_id"]))
        self.target_rack_box.setCurrentIndex(max(actual_index, 0))
        self.target_rack_box.blockSignals(False)
        self.target_start_u.blockSignals(True)
        self.target_start_u.setValue(int(row["start_u"] or 1))
        self.target_start_u.blockSignals(False)
        self.move_drawer.show()
        self._update_move_preview()

    def _schedule_move_preview(self, _value: Any = None) -> None:
        self.preview_timer.start()

    def _target_values(self) -> tuple[str, int, int] | None:
        if self.session is None:
            return None
        row = self._device_row(self._selected_device)
        rack_id = self.target_rack_box.currentData()
        if row is None or row["height_u"] is None or not rack_id:
            return None
        rack = next(
            (
                item
                for item in self.session.rack_rows()
                if item["rack_id"] == str(rack_id)
            ),
            None,
        )
        if rack is None:
            return None
        height = int(row["height_u"])
        maximum_start = max(1, int(rack["height_u"]) - height + 1)
        self.target_start_u.setMaximum(maximum_start)
        start_u = min(self.target_start_u.value(), maximum_start)
        end_u = start_u + height - 1
        return str(rack_id), start_u, end_u

    def _update_move_preview(self) -> None:
        values = self._target_values()
        if self.session is None or self._selected_device is None or values is None:
            self._set_preview_state("neutral", "等待选择位置", "请选择设备和目标位置。")
            self.drawer_add_button.setEnabled(False)
            return
        rack_id, start_u, end_u = values
        self.target_range_label.setText(f"目标范围：U{start_u}–U{end_u}")
        plan = self.session.preview_staged_move(
            self._selected_device,
            rack_id,
            start_u,
            end_u,
        )
        if plan.conflicts:
            conflict = plan.conflicts[0]
            self._set_preview_state(
                "error",
                "发现冲突",
                friendly_conflict_text(conflict.code, conflict.message, conflict.severity),
            )
            self.drawer_add_button.setEnabled(False)
        elif not any(action.device_id == self._selected_device for action in plan.actions):
            self._set_preview_state("neutral", "当前位置", "设备已经位于这个位置，无需更改。")
            self.drawer_add_button.setEnabled(False)
        else:
            rack_name = self.target_rack_box.currentText()
            self._set_preview_state(
                "success",
                "冲突检查通过",
                f"{rack_name} 的 U{start_u}–U{end_u} 可放置该设备。",
            )
            self.drawer_add_button.setEnabled(True)
        self._refresh_exceptions()

    def _set_preview_state(self, state: str, title: str, message: str) -> None:
        names = {
            "neutral": "previewNeutral",
            "success": "previewSuccess",
            "error": "previewError",
        }
        self.preview_box.setObjectName(names[state])
        self.preview_box.style().unpolish(self.preview_box)
        self.preview_box.style().polish(self.preview_box)
        self.preview_title.setText(title)
        self.preview_message.setText(message)

    def _stage_drawer_move(self) -> None:
        values = self._target_values()
        if self.session is None or self._selected_device is None or values is None:
            return
        rack_id, start_u, end_u = values
        plan = self.session.stage_move(
            self._selected_device,
            rack_id,
            start_u,
            end_u,
        )
        if plan.conflicts:
            conflict = plan.conflicts[0]
            self._set_preview_state(
                "error",
                "发现冲突",
                friendly_conflict_text(conflict.code, conflict.message, conflict.severity),
            )
            return
        self.move_drawer.hide()
        self._refresh_all()

    def _cancel_move_drawer(self) -> None:
        self.preview_timer.stop()
        self.move_drawer.hide()
        if self.session is not None:
            self.session.last_plan = None
            self._refresh_exceptions()

    def _remove_pending(self, device_id: str) -> None:
        if self.session is None:
            return
        self.session.remove_pending_move(device_id)
        self._refresh_all()

    def _clear_pending(self) -> None:
        if self.session is None or not self.session.pending_moves:
            return
        if not self._confirm_discard_pending("清空全部待同步更改"):
            return
        self.session.clear_pending_moves()
        self._refresh_all()

    def _show_pending_panel(self) -> None:
        self.pending_panel.setVisible(True)
        self.pending_table.setFocus()

    def _sync_pending(self) -> None:
        if self.session is None or not self.session.pending_moves:
            return
        count = len(self.session.pending_moves)
        answer = self.QtWidgets.QMessageBox.question(
            self.window,
            "确认同步更改",
            f"将 {count} 项更改写入源工作簿。\n\n"
            "RackTool 会先备份，再通过临时文件写入并重载验证。是否继续？",
            self.QtWidgets.QMessageBox.StandardButton.Cancel
            | self.QtWidgets.QMessageBox.StandardButton.Yes,
            self.QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        if answer != self.QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.session.apply_pending_moves()
        except Exception as error:  # noqa: BLE001
            self._show_error("同步未完成", error)
            self._refresh_all()
            return
        self._refresh_all()
        if result.status == "applied":
            self.QtWidgets.QMessageBox.information(
                self.window,
                "同步完成",
                f"已安全写入 {len(result.plan.actions)} 项更改，并创建备份。",
            )
        else:
            conflicts = result.plan.conflicts
            friendly = "\n\n".join(
                friendly_conflict_text(item.code, item.message, item.severity)
                for item in conflicts[:5]
            )
            box = self.QtWidgets.QMessageBox(self.window)
            box.setIcon(self.QtWidgets.QMessageBox.Icon.Warning)
            box.setWindowTitle("同步未完成")
            box.setText("同步未完成。为保护源文件，这次操作没有改写 Excel。")
            box.setInformativeText(friendly or result.message)
            box.setDetailedText("\n".join(result.errors[:8]))
            box.exec()

    def _open_workbook(self) -> None:
        path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "打开工作簿",
            "",
            "Excel 工作簿 (*.xlsx)",
        )
        if not path:
            return
        if not self._confirm_discard_pending("打开另一个工作簿"):
            return
        workbook = Path(path)
        try:
            self.load_session(
                GuiSession.open_workbook(workbook, default_database_path(workbook))
            )
        except Exception as error:  # noqa: BLE001
            self._show_error("无法打开工作簿", error)

    def _open_project(self) -> None:
        path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "打开项目",
            "",
            "RackTool 项目 (*.sqlite)",
        )
        if not path:
            return
        if not self._confirm_discard_pending("打开另一个项目"):
            return
        try:
            self.load_session(GuiSession.open_project(Path(path)))
        except Exception as error:  # noqa: BLE001
            self._show_error("无法打开项目", error)

    def _rescan(self) -> None:
        if self.session is None:
            return
        if not self._confirm_discard_pending("重新扫描"):
            return
        try:
            self.session.rescan()
            self._refresh_all()
        except Exception as error:  # noqa: BLE001
            self._show_error("重新扫描失败", error)

    def _export_json(self) -> None:
        if self.session is None:
            return
        path, _selected_filter = self.QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "导出 JSON",
            str(self.session.workbook_path.with_suffix(".json")),
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            self.session.export_json(Path(path))
            self._refresh_all()
        except Exception as error:  # noqa: BLE001
            self._show_error("导出失败", error)

    def _restore_backup(self) -> None:
        if self.session is None:
            return
        if not self._confirm_discard_pending("恢复备份"):
            return
        backups = self.session.backups()
        if not backups:
            self.QtWidgets.QMessageBox.information(
                self.window,
                "恢复备份",
                "还没有可用备份。",
            )
            return
        names = [item.name for item in backups]
        chosen, accepted = self.QtWidgets.QInputDialog.getItem(
            self.window,
            "恢复备份",
            "选择备份",
            names,
            0,
            False,
        )
        if not accepted:
            return
        backup = next(item for item in backups if item.name == chosen)
        try:
            self.session.restore_backup(backup)
            self._refresh_all()
        except Exception as error:  # noqa: BLE001
            self._show_error("恢复失败", error)

    def _show_error(self, title: str, error: Exception) -> None:
        box = self.QtWidgets.QMessageBox(self.window)
        box.setIcon(self.QtWidgets.QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(friendly_exception(error))
        box.setInformativeText("为保护源文件，这次失败的操作没有写入 Excel。")
        box.setDetailedText(f"{type(error).__name__}: {error}")
        box.exec()

    def _confirm_discard_pending(self, action: str) -> bool:
        if self.session is None or not self.session.pending_moves:
            return True
        answer = self.QtWidgets.QMessageBox.warning(
            self.window,
            "待同步更改尚未提交",
            f"{action}会丢弃当前 {len(self.session.pending_moves)} 项待同步更改。是否继续？",
            self.QtWidgets.QMessageBox.StandardButton.Cancel
            | self.QtWidgets.QMessageBox.StandardButton.Discard,
            self.QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        return bool(answer == self.QtWidgets.QMessageBox.StandardButton.Discard)

    @staticmethod
    def _format_u_range(start_u: Any, end_u: Any) -> str:
        if start_u is None or end_u is None:
            return "—"
        low = min(int(start_u), int(end_u))
        high = max(int(start_u), int(end_u))
        return f"U{low}" if low == high else f"U{low}–U{high}"
    def _open_exceptions(self, *_args: Any) -> None:
        self._set_page(self.PAGE_EXCEPTIONS)

    def _toggle_exception_technical(self, expanded: bool) -> None:
        self.exception_technical.setVisible(expanded)
        self.exception_technical_toggle.setText(
            "⌄  技术详情" if expanded else "›  技术详情"
        )

    def _on_exception_selected(self) -> None:
        row_index = self.exception_table.currentRow()
        item = self.exception_table.item(row_index, 0) if row_index >= 0 else None
        detail = ""
        if item is not None:
            detail = str(item.data(self.QtCore.Qt.ItemDataRole.UserRole) or "")
        self.exception_technical.setPlainText(detail or "当前没有可展开的技术详情。")

    def _refresh_device_filter_options(self) -> None:
        if self.session is None:
            return
        current = self.device_rack_filter.currentData()
        self.device_rack_filter.blockSignals(True)
        self.device_rack_filter.clear()
        self.device_rack_filter.addItem("全部机柜", "")
        for rack in self.session.rack_rows(sort_by="name"):
            self.device_rack_filter.addItem(str(rack["rack_name"]), str(rack["rack_id"]))
        index = self.device_rack_filter.findData(current)
        self.device_rack_filter.setCurrentIndex(max(index, 0))
        self.device_rack_filter.blockSignals(False)

    def _refresh_overview_sheet_names(self) -> None:
        if self.session is None:
            self.overview_sheet_box.clear()
            self.overview_scene.clear()
            return
        current = self.overview_sheet_box.currentData()
        names = self.session.overview_sheet_names()
        self.overview_sheet_box.blockSignals(True)
        self.overview_sheet_box.clear()
        for name in names:
            self.overview_sheet_box.addItem(name, name)
        if current:
            index = self.overview_sheet_box.findData(current)
            self.overview_sheet_box.setCurrentIndex(max(index, 0))
        elif names:
            self.overview_sheet_box.setCurrentIndex(0)
        self.overview_sheet_box.blockSignals(False)
        self._render_overview_sheet()

    def _fit_overview_view(self) -> None:
        if not self.overview_scene.items():
            return
        self.overview_view.resetTransform()
        self.overview_view.fitInView(
            self.overview_scene.sceneRect(),
            self.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        )

    def _axis_positions(
        self,
        count: int,
        sizes: dict[int, float],
        default: float,
        scale: float,
        minimum: float,
    ) -> list[float]:
        positions = [0.0, 0.0]
        for index in range(1, count + 1):
            size = max(minimum, float(sizes.get(index, default)) * scale)
            positions.append(positions[-1] + size)
        return positions

    def _sheet_rect(
        self,
        bounds: tuple[int, int, int, int],
        col_pos: list[float],
        row_pos: list[float],
    ) -> tuple[float, float, float, float]:
        min_col, min_row, max_col, max_row = bounds
        max_col = min(max_col, len(col_pos) - 2)
        max_row = min(max_row, len(row_pos) - 2)
        min_col = min(max(min_col, 1), max_col)
        min_row = min(max(min_row, 1), max_row)
        x = col_pos[min_col]
        y = row_pos[min_row]
        width = max(col_pos[max_col + 1] - x, 12.0)
        height = max(row_pos[max_row + 1] - y, 10.0)
        return x, y, width, height

    def _add_sheet_label(
        self,
        text: str,
        x: float,
        y: float,
        width: float,
        color: str,
        size: float = 8.0,
    ) -> None:
        label = self.overview_scene.addText("")
        label.setPlainText(cell_display_text(text))
        font = label.font()
        font.setPointSizeF(size)
        label.setFont(font)
        label.setDefaultTextColor(self.QtGui.QColor(color))
        label.document().setDocumentMargin(1)
        label.setTextWidth(max(width - 6, 20))
        label.setPos(x + 3, y + 2)
        label.setAcceptedMouseButtons(self.QtCore.Qt.MouseButton.NoButton)

    def _render_overview_sheet(self, *_args: Any) -> None:
        self.overview_scene.clear()
        if self.session is None:
            return
        sheet_name = self.overview_sheet_box.currentData()
        if not sheet_name:
            note = self.overview_scene.addText("没有可预览的机柜工作表。")
            note.setDefaultTextColor(self.QtGui.QColor("#667085"))
            self.overview_scene.setSceneRect(0, 0, 360, 80)
            return
        try:
            sheet = self.session.overview_sheet(str(sheet_name))
        except Exception as error:  # noqa: BLE001
            note = self.overview_scene.addText(friendly_exception(error))
            note.setTextWidth(420)
            note.setDefaultTextColor(self.QtGui.QColor("#b42318"))
            self.overview_scene.setSceneRect(0, 0, 460, 120)
            return

        max_column = max(int(sheet["max_column"]), 1)
        max_row = max(int(sheet["max_row"]), 1)
        col_pos = self._axis_positions(
            max_column,
            {int(key): float(value) for key, value in sheet["column_widths"].items()},
            float(sheet["default_column_width"]),
            7.0 * 0.42,
            16.0,
        )
        row_pos = self._axis_positions(
            max_row,
            {int(key): float(value) for key, value in sheet["row_heights"].items()},
            float(sheet["default_row_height"]),
            (96.0 / 72.0) * 0.42,
            10.0,
        )
        sheet_width = col_pos[-1] + 24
        sheet_height = row_pos[-1] + 24
        self.overview_scene.addRect(
            0,
            0,
            sheet_width,
            sheet_height,
            self.QtGui.QPen(self.QtGui.QColor("#d5dce6"), 1),
            self.QtGui.QBrush(self.QtGui.QColor("#fbfcfe")),
        )
        for block in sheet["context_blocks"]:
            x, y, width, height = self._sheet_rect(block["source_bounds"], col_pos, row_pos)
            self.overview_scene.addRect(
                x,
                y,
                width,
                height,
                self.QtGui.QPen(self.QtGui.QColor("#d0d7e2"), 1),
                self.QtGui.QBrush(self.QtGui.QColor("#f3f6fb")),
            )
            self._add_sheet_label(str(block["display_text"]), x, y, width, "#475467", 7.5)
        palette = ("#dbeafe", "#dcfce7", "#f3e8ff", "#ffedd5", "#cffafe")
        for rack_index, rack in enumerate(sheet["racks"]):
            x, y, width, height = self._sheet_rect(rack["bounds"], col_pos, row_pos)
            fill = palette[rack_index % len(palette)]
            rect = self.overview_scene.addRect(
                x,
                y,
                width,
                height,
                self.QtGui.QPen(self.QtGui.QColor("#3b82f6"), 1.6),
                self.QtGui.QBrush(self.QtGui.QColor(fill)),
            )
            rect.setData(0, str(rack["rack_id"]))
            rect.setFlag(
                self.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                True,
            )
            title = f"{rack['rack_name']}\n{rack['height_u']}U"
            self._add_sheet_label(title, x, y, width, "#17335f", 8.5)
            for device in rack["devices"]:
                device_bounds = device.get("source_bounds")
                if not device_bounds:
                    continue
                dx, dy, dw, dh = self._sheet_rect(device_bounds, col_pos, row_pos)
                self.overview_scene.addRect(
                    dx,
                    dy,
                    dw,
                    dh,
                    self.QtGui.QPen(self.QtGui.QColor("#64748b"), 1),
                    self.QtGui.QBrush(self.QtGui.QColor("#ffffff")),
                )
                self._add_sheet_label(
                    str(device["display_text"]),
                    dx,
                    dy,
                    dw,
                    "#1f2937",
                    7.0,
                )
        self.overview_scene.setSceneRect(0, 0, sheet_width, sheet_height)
        if sheet.get("context_truncated"):
            self.overview_status.setText(
                f"{self.session.status_message}  工作表视图已截断部分背景文字，机柜和设备位置仍完整。"
            )
        self.QtCore.QTimer.singleShot(0, self._fit_overview_view)

    def _on_overview_selection_changed(self) -> None:
        try:
            selected = self.overview_scene.selectedItems()
        except RuntimeError:
            return
        if not selected:
            return
        rack_id = selected[0].data(0)
        if not rack_id:
            return
        self._selected_rack = str(rack_id)
        self._refresh_rack_list()
        self._set_page(self.PAGE_RACKS)


def launch(workbook: Path | None = None) -> int:
    app = create_app()
    cockpit = CockpitWindow()
    if workbook is not None:
        cockpit.load_session(GuiSession.open_workbook(workbook))
    cockpit.widget().show()
    result = app.exec()
    return int(result)


def launch_main() -> None:
    import sys

    workbook = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    raise SystemExit(launch(workbook))
