from __future__ import annotations

from pathlib import Path
from typing import Any

from racktool.gui.session import GuiSession, default_database_path


def _require_qt() -> Any:
    try:
        from PySide6 import QtWidgets  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(
            "RackTool GUI requires PySide6. Install it with: pip install 'racktool[gui]'"
        ) from error
    return QtWidgets


def create_app(argv: list[str] | None = None) -> Any:
    QtWidgets = _require_qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(argv or [])
        app.setApplicationName("RackTool")
        app.setOrganizationName("RackTool")
    return app


class CockpitWindow:
    def __init__(self) -> None:
        QtWidgets = _require_qt()
        self.QtWidgets = QtWidgets
        self.session: GuiSession | None = None
        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("RackTool")
        self.window.resize(1280, 800)

        self.device_table = QtWidgets.QTableWidget(0, 8)
        self.device_table.setHorizontalHeaderLabels(
            ["设备ID", "显示文本", "机柜", "起始U", "结束U", "高度", "状态", "来源"]
        )
        self.device_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.device_table.itemSelectionChanged.connect(self._on_device_selected)

        self.rack_table = QtWidgets.QTableWidget(0, 5)
        self.rack_table.setHorizontalHeaderLabels(["机柜ID", "名称", "Sheet", "高度U", "已占用U"])
        self.rack_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.rack_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.rack_table.itemSelectionChanged.connect(self._on_rack_selected)

        self.occupancy_table = QtWidgets.QTableWidget(0, 2)
        self.occupancy_table.setHorizontalHeaderLabels(["U", "设备"])
        self.occupancy_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.mapping_table = QtWidgets.QTableWidget(0, 5)
        self.mapping_table.setHorizontalHeaderLabels(
            ["类型", "实体ID", "Sheet", "来源范围", "指纹"]
        )
        self.mapping_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.conflict_table = QtWidgets.QTableWidget(0, 3)
        self.conflict_table.setHorizontalHeaderLabels(["级别", "代码", "说明"])
        self.conflict_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.rack_box = QtWidgets.QComboBox()
        self.start_u = QtWidgets.QSpinBox()
        self.start_u.setRange(1, 100)
        self.end_u = QtWidgets.QSpinBox()
        self.end_u.setRange(1, 100)
        preview_button = QtWidgets.QPushButton("预览冲突")
        preview_button.clicked.connect(self._preview_move)
        sync_button = QtWidgets.QPushButton("同步写回")
        sync_button.clicked.connect(self._apply_move)

        move_bar = QtWidgets.QWidget()
        move_layout = QtWidgets.QHBoxLayout(move_bar)
        move_layout.addWidget(QtWidgets.QLabel("目标机柜"))
        move_layout.addWidget(self.rack_box)
        move_layout.addWidget(QtWidgets.QLabel("起始U"))
        move_layout.addWidget(self.start_u)
        move_layout.addWidget(QtWidgets.QLabel("结束U"))
        move_layout.addWidget(self.end_u)
        move_layout.addWidget(preview_button)
        move_layout.addWidget(sync_button)
        move_layout.addStretch(1)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addWidget(QtWidgets.QLabel("设备清单"))
        left_layout.addWidget(self.device_table)

        center = QtWidgets.QWidget()
        center_layout = QtWidgets.QVBoxLayout(center)
        center_layout.addWidget(QtWidgets.QLabel("机柜"))
        center_layout.addWidget(self.rack_table, 1)
        center_layout.addWidget(QtWidgets.QLabel("机柜 U 位"))
        center_layout.addWidget(self.occupancy_table, 2)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.addWidget(QtWidgets.QLabel("Mapping"))
        right_layout.addWidget(self.mapping_table, 1)
        right_layout.addWidget(QtWidgets.QLabel("异常 / 冲突"))
        right_layout.addWidget(self.conflict_table, 1)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)

        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.addWidget(splitter, 1)
        root_layout.addWidget(move_bar)
        self.window.setCentralWidget(root)
        self.window.statusBar().showMessage("打开工作簿或项目以开始")

        file_menu = self.window.menuBar().addMenu("文件")
        file_menu.addAction("打开工作簿…", self._open_workbook)
        file_menu.addAction("打开项目…", self._open_project)
        file_menu.addSeparator()
        file_menu.addAction("重新扫描", self._rescan)
        file_menu.addAction("导出 JSON…", self._export_json)
        file_menu.addAction("恢复备份…", self._restore_backup)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.window.close)

    def widget(self) -> Any:
        return self.window

    def load_session(self, session: GuiSession) -> None:
        self.session = session
        self._refresh()

    def _selected_device_id(self) -> str | None:
        row = self.device_table.currentRow()
        if row < 0:
            return None
        item = self.device_table.item(row, 0)
        return item.text() if item is not None else None

    def _selected_rack_id(self) -> str | None:
        row = self.rack_table.currentRow()
        if row < 0:
            data = self.rack_box.currentData()
            return str(data) if data else None
        item = self.rack_table.item(row, 0)
        return item.text() if item is not None else None

    def _fill_table(self, table: Any, rows: list[list[str]]) -> None:
        table.setRowCount(len(rows))
        QtWidgets = self.QtWidgets
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QtWidgets.QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def _refresh(self) -> None:
        if self.session is None:
            return
        current_device = self._selected_device_id()
        current_rack = self._selected_rack_id()
        device_rows = self.session.device_rows()
        self._fill_table(
            self.device_table,
            [
                [
                    row["device_id"],
                    row["display_text"].replace("\n", " / "),
                    row["rack_name"],
                    "" if row["start_u"] is None else str(row["start_u"]),
                    "" if row["end_u"] is None else str(row["end_u"]),
                    "" if row["height_u"] is None else str(row["height_u"]),
                    str(row["status"]),
                    f"{row['sheet_name']} {row['source_range']}".strip(),
                ]
                for row in device_rows
            ],
        )
        rack_rows = self.session.rack_rows()
        self._fill_table(
            self.rack_table,
            [
                [
                    row["rack_id"],
                    row["rack_name"],
                    row["sheet_name"],
                    str(row["height_u"]),
                    str(row["occupied_u"]),
                ]
                for row in rack_rows
            ],
        )
        self.rack_box.blockSignals(True)
        self.rack_box.clear()
        for row in rack_rows:
            self.rack_box.addItem(f"{row['rack_name']} ({row['rack_id']})", row["rack_id"])
        self.rack_box.blockSignals(False)
        mappings = self.session.mapping_rows()
        self._fill_table(
            self.mapping_table,
            [
                [
                    str(item.get("mapping_kind", "")),
                    str(item.get("device_id") or item.get("rack_id") or ""),
                    str(item.get("sheet_name", "")),
                    str(item.get("source_range", "")),
                    str(item.get("workbook_fingerprint", ""))[:12],
                ]
                for item in mappings
            ],
        )
        conflicts = self.session.conflict_rows()
        self._fill_table(
            self.conflict_table,
            [
                [str(item.get("severity", "")), str(item.get("code", "")), str(item.get("message", ""))]
                for item in conflicts
            ],
        )
        if current_device:
            for row_index in range(self.device_table.rowCount()):
                item = self.device_table.item(row_index, 0)
                if item is not None and item.text() == current_device:
                    self.device_table.selectRow(row_index)
                    break
        if current_rack:
            index = int(self.rack_box.findData(current_rack))
            if index >= 0:
                self.rack_box.setCurrentIndex(index)
            for row_index in range(self.rack_table.rowCount()):
                item = self.rack_table.item(row_index, 0)
                if item is not None and item.text() == current_rack:
                    self.rack_table.selectRow(row_index)
                    break
        self._refresh_occupancy()
        self.window.statusBar().showMessage(self.session.status_message)
        title = f"RackTool — {self.session.workbook_path.name}"
        self.window.setWindowTitle(title)

    def _refresh_occupancy(self) -> None:
        if self.session is None:
            return
        rack_id = self._selected_rack_id()
        if not rack_id:
            self.occupancy_table.setRowCount(0)
            return
        rows = self.session.occupancy_rows(rack_id)
        self._fill_table(
            self.occupancy_table,
            [[str(row["u"]), str(row["display_text"]).replace("\n", " / ")] for row in rows],
        )

    def _on_device_selected(self) -> None:
        if self.session is None:
            return
        device_id = self._selected_device_id()
        if device_id is None:
            return
        row = next((item for item in self.session.device_rows() if item["device_id"] == device_id), None)
        if row is None:
            return
        if row["rack_id"]:
            index = int(self.rack_box.findData(row["rack_id"]))
            if index >= 0:
                self.rack_box.setCurrentIndex(index)
        if row["start_u"]:
            self.start_u.setValue(int(row["start_u"]))
        if row["end_u"]:
            self.end_u.setValue(int(row["end_u"]))

    def _on_rack_selected(self) -> None:
        rack_id = self._selected_rack_id()
        if rack_id:
            index = int(self.rack_box.findData(rack_id))
            if index >= 0:
                self.rack_box.setCurrentIndex(index)
        self._refresh_occupancy()

    def _open_workbook(self) -> None:
        path, _checked = self.QtWidgets.QFileDialog.getOpenFileName(
            self.window, "打开工作簿", "", "Excel (*.xlsx)"
        )
        if not path:
            return
        workbook = Path(path)
        self.load_session(GuiSession.open_workbook(workbook, default_database_path(workbook)))

    def _open_project(self) -> None:
        path, _checked = self.QtWidgets.QFileDialog.getOpenFileName(
            self.window, "打开项目", "", "RackTool 项目 (*.sqlite)"
        )
        if not path:
            return
        self.load_session(GuiSession.open_project(Path(path)))

    def _rescan(self) -> None:
        if self.session is None:
            return
        self.session.rescan()
        self._refresh()

    def _export_json(self) -> None:
        if self.session is None:
            return
        path, _checked = self.QtWidgets.QFileDialog.getSaveFileName(
            self.window, "导出 JSON", str(self.session.workbook_path.with_suffix(".json")), "JSON (*.json)"
        )
        if not path:
            return
        self.session.export_json(Path(path))
        self._refresh()

    def _restore_backup(self) -> None:
        if self.session is None:
            return
        backups = self.session.backups()
        if not backups:
            self.QtWidgets.QMessageBox.information(self.window, "恢复备份", "还没有可用备份。")
            return
        names = [item.name for item in backups]
        chosen, accepted = self.QtWidgets.QInputDialog.getItem(
            self.window, "恢复备份", "选择备份", names, 0, False
        )
        if not accepted:
            return
        backup = next(item for item in backups if item.name == chosen)
        self.session.restore_backup(backup)
        self._refresh()

    def _preview_move(self) -> None:
        if self.session is None:
            return
        device_id = self._selected_device_id()
        rack_id = str(self.rack_box.currentData() or "")
        if not device_id or not rack_id:
            self.QtWidgets.QMessageBox.warning(self.window, "预览冲突", "请先选择设备和目标机柜。")
            return
        plan = self.session.plan_move(device_id, rack_id, self.start_u.value(), self.end_u.value())
        self._refresh()
        if plan.conflicts:
            self.QtWidgets.QMessageBox.warning(
                self.window,
                "冲突",
                "\n".join(item.message for item in plan.conflicts),
            )

    def _apply_move(self) -> None:
        if self.session is None:
            return
        device_id = self._selected_device_id()
        rack_id = str(self.rack_box.currentData() or "")
        if not device_id or not rack_id:
            self.QtWidgets.QMessageBox.warning(self.window, "同步写回", "请先选择设备和目标机柜。")
            return
        plan = self.session.plan_move(device_id, rack_id, self.start_u.value(), self.end_u.value())
        if plan.conflicts:
            self._refresh()
            self.QtWidgets.QMessageBox.warning(
                self.window,
                "写回已拒绝",
                "\n".join(item.message for item in plan.conflicts),
            )
            return
        result = self.session.apply_move()
        self._refresh()
        if result.status != "applied":
            self.QtWidgets.QMessageBox.warning(
                self.window,
                "写回未完成",
                result.message + ("\n" + "\n".join(result.errors) if result.errors else ""),
            )


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
