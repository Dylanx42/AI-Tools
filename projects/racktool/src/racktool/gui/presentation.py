from __future__ import annotations

_ISSUE_COPY: dict[str, tuple[str, str]] = {
    "unresolved-u-axis": (
        "发现疑似 U 位编号，但旁边没有识别到机柜标题",
        "这是一条提醒，不会阻止同步。如果这里确实是机柜，请在源 Excel 中补齐或合并机柜标题，保存后重新扫描；如果只是普通编号，可以不处理。",
    ),
    "duplicate-rack-title": (
        "多个位置使用了相同的机柜名称",
        "请确认这些位置是否代表同一个机柜；如果不是，请在源 Excel 中改成可区分的名称，保存后重新扫描。",
    ),
    "non-text-device-candidate": (
        "设备区域里出现了不是文字的内容",
        "请在源 Excel 中检查对应单元格，确认它是设备名称、公式还是普通数字；修正并保存后重新扫描。",
    ),
    "overlapping-placement-candidates": (
        "有多个设备占用了同一个 U 位",
        "请回到源 Excel 检查重叠区域，保留正确设备位置后保存并重新扫描。",
    ),
    "overlapping-active-placements": (
        "项目中有设备位置互相重叠",
        "请先修正源 Excel 中的重叠设备位置，再重新扫描。重叠消除前不会写回。",
    ),
    "target-u-occupied": (
        "目标 U 位已经有设备",
        "返回机柜页面，为设备选择一段完整空闲的 U 位。",
    ),
    "plan-target-overlap": (
        "两条待同步更改选择了重叠的 U 位",
        "返回机柜页面，移除或修改其中一条待同步更改。",
    ),
    "plan-cell-range-overlap": (
        "两条待同步更改会修改同一片 Excel 区域",
        "请拆开目标位置，或一次只同步其中一条更改。",
    ),
    "stale-project-fingerprint": (
        "源 Excel 在项目打开后发生了变化",
        "先保存源 Excel，再点击“重新扫描”。重新扫描完成前不会写回。",
    ),
    "wrong-source-workbook": (
        "当前工作簿不是这个项目绑定的源文件",
        "请重新打开与项目对应的源 Excel；不要用另一个同名副本直接写回。",
    ),
    "source-workbook-missing": (
        "找不到项目绑定的源 Excel",
        "请把源文件恢复到原位置，或重新导入正确的工作簿。",
    ),
    "unbound-project-source": (
        "项目没有绑定可写回的源 Excel",
        "请重新从源工作簿创建项目。",
    ),
    "cross-sheet-move-unsupported": (
        "当前版本不能把设备移动到另一个工作表",
        "请选择同一工作表内的机柜；跨工作表移动需要在 Excel 中人工完成后重新扫描。",
    ),
    "device-height-change": (
        "目标位置没有保留设备原来的 U 高度",
        "请重新选择起始 U 位；RackTool 会按设备原高度自动计算结束 U 位。",
    ),
    "u-out-of-bounds": (
        "目标 U 位超出了机柜范围",
        "请选择机柜有效范围内的起始 U 位。",
    ),
    "u-axis-gap": (
        "目标位置对应的 U 位编号不连续",
        "请检查源 Excel 的 U 位编号是否缺失或重复，修正后重新扫描。",
    ),
    "target-rack-missing": (
        "目标机柜已不存在",
        "重新扫描项目，并选择当前仍存在的机柜。",
    ),
    "source-device-text-mismatch": (
        "源 Excel 中的设备文字已经变化",
        "先点击“重新扫描”接收最新文字，再重新安排移动。",
    ),
    "invalid-stored-profile": (
        "项目保存的布局规则已损坏或不完整",
        "请重新导入经过验证的布局规则，再重新扫描工作簿。",
    ),
    "ambiguous-device-identity": (
        "重新扫描时无法唯一确认设备身份",
        "请在源 Excel 中让这些设备的名称或位置更容易区分，保存后重新扫描。系统不会在证据不足时猜测。",
    ),
    "competing-device-identity": (
        "多台设备的身份证据互相冲突",
        "请检查源 Excel 中是否有重复设备或位置被改乱，修正后保存并重新扫描。",
    ),
    "conflicting-device-identity-evidence": (
        "设备身份证据互相矛盾",
        "请核对源 Excel 中的设备文字、位置和格式是否被同时改动，修正后重新扫描。",
    ),
    "ambiguous-rack-identity": (
        "无法唯一确认机柜身份",
        "请在源 Excel 中让机柜名称或位置更容易区分，保存后重新扫描。",
    ),
    "stale-write-plan": (
        "当前待同步计划已经过期",
        "请重新扫描或重新加入待同步更改后再同步。过期计划不会写入源文件。",
    ),
    "unsupported-threaded-comments": (
        "相关区域包含当前版本无法安全保留的现代批注",
        "请先在 Excel 中移开或删除这些现代批注，保存后重新扫描。RackTool 不会冒险覆盖它们。",
    ),
    "unsupported-cell-comment": (
        "相关单元格包含当前版本无法安全保留的批注",
        "请先在 Excel 中移开或删除这些批注，保存后重新扫描。",
    ),
    "unsupported-cell-hyperlink": (
        "相关单元格包含当前版本无法安全保留的超链接",
        "请先在 Excel 中移开或删除这些超链接，保存后重新扫描。",
    ),
    "unsupported-data-validation": (
        "相关区域包含当前版本无法安全保留的数据验证",
        "请先在 Excel 中移开或删除这些数据验证，保存后重新扫描。",
    ),
}

_STATUS_COPY = {
    "active": "正常",
    "missing": "源表中已不存在",
    "unplaced": "未放置",
}


def friendly_issue(code: str, message: str, severity: str) -> dict[str, str]:
    title_guidance = _ISSUE_COPY.get(code)
    if title_guidance is None:
        title_guidance = _category_copy(code)
    title, guidance = title_guidance
    level = "需要处理" if severity == "error" else "提醒（不阻止同步）"
    return {
        "level": level,
        "title": title,
        "guidance": guidance,
        "technical_detail": f"{code}: {message}",
    }


def friendly_exception(error: Exception) -> str:
    if isinstance(error, FileNotFoundError):
        return "找不到所选文件。请确认文件没有被移动、改名或删除。"
    if isinstance(error, PermissionError):
        return "没有权限读取或更新这个文件。请关闭占用它的程序，并检查文件权限。"
    if isinstance(error, IsADirectoryError):
        return "选择的是文件夹，请重新选择一个 Excel 工作簿或 RackTool 项目文件。"
    if isinstance(error, ValueError):
        return "这个文件或操作不符合 RackTool 的安全要求，请检查选择后重试。"
    if isinstance(error, OSError):
        return "系统无法完成文件操作。请确认磁盘空间、文件权限和文件占用状态。"
    return "操作没有完成。为保护源文件，RackTool 已停止本次操作。"


def cell_display_text(value: str) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def friendly_status(status: str) -> str:
    return _STATUS_COPY.get(status, "需关注")


def friendly_conflict_text(code: str, message: str, severity: str = "error") -> str:
    copy = friendly_issue(code, message, severity)
    return f"{copy['title']}\n{copy['guidance']}"


def _category_copy(code: str) -> tuple[str, str]:
    if code.startswith("unsupported-"):
        return (
            "相关 Excel 区域包含当前版本无法安全保留的功能",
            "请检查对应区域中的批注、超链接、数据验证、名称或现代批注。移除或移开这些内容后重新扫描；RackTool 不会冒险覆盖。",
        )
    if "ambiguous" in code or "competing" in code or "conflicting" in code:
        return (
            "RackTool 无法唯一确认设备或机柜身份",
            "请在源 Excel 中让名称、位置或格式更容易区分，保存后重新扫描。系统不会在证据不足时猜测。",
        )
    if "duplicate" in code:
        return (
            "项目中发现了重复记录",
            "请检查源 Excel 是否存在重复机柜、设备或位置，修正后重新扫描。",
        )
    if "mapping" in code or "placement" in code or "reference" in code:
        return (
            "设备位置与源 Excel 的对应关系不一致",
            "请先重新扫描；如果仍然出现，请在源 Excel 中核对设备所在机柜和 U 位后再次导入。",
        )
    if "stale" in code or "fingerprint" in code or "source" in code:
        return (
            "项目记录与当前源 Excel 不一致",
            "请保存源 Excel 后重新扫描，再重新执行刚才的操作。",
        )
    if "overlap" in code or "occupied" in code:
        return (
            "设备位置发生重叠",
            "返回机柜页面，选择一段完整空闲的 U 位；如果源表本身重叠，请先在 Excel 中修正并重新扫描。",
        )
    if "profile" in code or "layout" in code:
        return (
            "当前布局规则不能可靠解释这部分工作簿",
            "请检查或重新选择布局规则，确认后重新扫描。",
        )
    return (
        "发现一项无法自动处理的工作簿问题",
        "为保护源文件，RackTool 已停止相关操作。请检查源 Excel 后重新扫描；如问题仍在，可展开技术信息交给维护人员。",
    )
