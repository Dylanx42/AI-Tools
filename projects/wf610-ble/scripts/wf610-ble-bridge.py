#!/usr/bin/env python3
"""
WF610 BLE -> persistent PTY bridge.

The BLE connection and the PTY live independently from SecureCRT sessions:
start this process once, then open/close separate SecureCRT sessions against
the same PTY symlink for per-session logging.

Defaults are from the live WF610A / WF610BLE probe on this Mac:
Feasycom FSC-BT826B, Classic SPP as /dev/cu.WF610A, BLE GATT as FFF0.
FFF1 is console data notify, FFF2 is console data write, FFF3 is module
status and must not be copied into the PTY.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pty
import signal
import sys
import termios
import tty
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


BLE_BASE_UUID = "0000{}-0000-1000-8000-00805f9b34fb"


def normalize_uuid(value: str) -> str:
    value = value.strip().lower()
    if len(value) == 4 and all(c in "0123456789abcdef" for c in value):
        return BLE_BASE_UUID.format(value)
    return value


def log(level: str, message: str) -> None:
    print(f"[{level}] {message}", flush=True)


@dataclass
class Settings:
    target_name: Optional[str]
    target_address: Optional[str]
    service_uuid: str
    read_uuid: str
    write_uuid: str
    status_uuid: Optional[str]
    port_link: str
    scan_timeout: float
    reconnect_delay: float
    connect_timeout: float
    chunk_size: int
    write_delay: float
    state_file: str


class BlePtyBridge:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.slave_path: Optional[str] = None

        self.client: Any = None
        self.read_char: Any = None
        self.write_char: Any = None
        self.status_char: Any = None
        self.write_response = False

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.stop_event = asyncio.Event()
        self.connection_lost = asyncio.Event()
        self.ble_connected = asyncio.Event()
        self._last_no_link_warning = 0.0
        self._write_state("starting")

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        self._create_pty()
        log("READY", f"虚拟串口: {self.settings.port_link} -> {self.slave_path}")
        log("INFO", "PTY 会在 CRT 会话关闭后保留；可反复打开不同 SecureCRT session")
        self._write_state("scanning")

        pty_task = asyncio.create_task(self._pty_to_ble_loop(), name="pty-to-ble")
        ble_task = asyncio.create_task(self._ble_manager_loop(), name="ble-manager")
        try:
            await self.stop_event.wait()
        finally:
            for task in (pty_task, ble_task):
                task.cancel()
            await asyncio.gather(pty_task, ble_task, return_exceptions=True)
            await self._disconnect()
            self._close_pty()
            self._write_state("stopped")

    def request_stop(self) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.stop_event.set)

    def _create_pty(self) -> None:
        self.master_fd, self.slave_fd = pty.openpty()
        # Keep both ends in raw mode.  Keeping slave_fd open is intentional:
        # closing a CRT session must not destroy the PTY or BLE connection.
        tty.setraw(self.master_fd, termios.TCSANOW)
        tty.setraw(self.slave_fd, termios.TCSANOW)
        self.slave_path = os.ttyname(self.slave_fd)

        link = self.settings.port_link
        if os.path.lexists(link):
            if not os.path.islink(link):
                raise RuntimeError(f"拒绝覆盖现有非符号链接: {link}")
            os.unlink(link)
        os.symlink(self.slave_path, link)

    def _close_pty(self) -> None:
        link = self.settings.port_link
        if os.path.islink(link):
            try:
                if os.path.realpath(link) == self.slave_path or self.slave_path is None:
                    os.unlink(link)
            except OSError as exc:
                log("WARN", f"清理 PTY 符号链接失败: {exc}")

        for fd_name in ("master_fd", "slave_fd"):
            fd = getattr(self, fd_name)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_name, None)

    async def _ble_manager_loop(self) -> None:
        try:
            from bleak import BleakClient, BleakScanner
        except ImportError:
            log("ERROR", "当前 Python 没有 bleak；先安装到实际运行本脚本的 Python 环境")
            self.request_stop()
            return

        while not self.stop_event.is_set():
            try:
                target = await self._find_target(BleakScanner)
                if target is None:
                    self._write_state("scanning")
                    await self._wait_or_stop(self.settings.reconnect_delay)
                    continue

                self._write_state("connecting")
                await self._connect_and_wait(BleakClient, target)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log("ERROR", f"BLE 会话异常: {type(exc).__name__}: {exc}")
            finally:
                await self._disconnect()

            await self._wait_or_stop(self.settings.reconnect_delay)

    async def _find_target(self, scanner_cls: Any) -> Any:
        filters = []
        if self.settings.target_address:
            filters.append(f"address={self.settings.target_address}")
        if self.settings.target_name:
            filters.append(f"name={self.settings.target_name}")
        label = ", ".join(filters) or "未设置名称/地址"
        if self.settings.target_address:
            log("CONNECT", f"按已知地址主动连接 {self.settings.target_address} ({label})")
            return self.settings.target_address

        log("SCAN", f"未配置地址，扫描 {self.settings.scan_timeout:g}s ({label})")
        discovered = await scanner_cls.discover(
            timeout=self.settings.scan_timeout,
            return_adv=True,
        )
        for item in self._device_items(discovered):
            device, advertisement = item
            address = str(getattr(device, "address", ""))
            name = getattr(device, "name", None) or getattr(advertisement, "local_name", None)
            address_match = bool(
                self.settings.target_address
                and address.upper() == self.settings.target_address.upper()
            )
            name_match = bool(self.settings.target_name and name == self.settings.target_name)
            if address_match or name_match:
                rssi = getattr(advertisement, "rssi", "?")
                log("FOUND", f"{name or '<unnamed>'} @ {address} (rssi={rssi})")
                return device

        log("MISS", "没有找到目标 BLE 设备")
        return None

    @staticmethod
    def _device_items(discovered: Any) -> Iterable[tuple[Any, Any]]:
        if isinstance(discovered, dict):
            for value in discovered.values():
                if isinstance(value, tuple) and len(value) == 2:
                    yield value[0], value[1]
                else:
                    yield value, None
        else:
            for device in discovered:
                yield device, None

    async def _connect_and_wait(self, client_cls: Any, target: Any) -> None:
        address = getattr(target, "address", "unknown")
        log("CONNECT", f"连接 {getattr(target, 'name', None) or address}")
        client = client_cls(
            target,
            timeout=self.settings.connect_timeout,
            disconnected_callback=self._on_disconnect,
        )
        self.client = client
        self.connection_lost.clear()
        await client.connect()
        if not client.is_connected:
            raise RuntimeError("Bleak 报告连接未建立")

        self.read_char, self.write_char, self.write_response = self._resolve_characteristics(client)
        await client.start_notify(self.read_char, self._on_ble_data)
        if self.status_char is not None:
            await client.start_notify(self.status_char, self._on_status_data)
            log("GATT", f"status={self.status_char.uuid} (module status, not copied to PTY)")
        self.ble_connected.set()
        log("CONNECTED", f"{address}")
        self._write_state("connected")
        log(
            "GATT",
            f"read={self.read_char.uuid} notify; write={self.write_char.uuid}; "
            f"response={self.write_response}",
        )
        log("READY", f"BLE 桥接可用，CRT 请连接 {self.settings.port_link}")

        await self.connection_lost.wait()
        log("DISCONNECTED", "BLE 连接断开，保留 PTY 并自动重试")
        self._write_state("disconnected")

    def _resolve_characteristics(self, client: Any) -> tuple[Any, Any, bool]:
        wanted_service = normalize_uuid(self.settings.service_uuid)
        wanted_read = normalize_uuid(self.settings.read_uuid)
        wanted_write = normalize_uuid(self.settings.write_uuid)
        wanted_status = (
            normalize_uuid(self.settings.status_uuid) if self.settings.status_uuid else None
        )
        read_char = None
        write_char = None
        write_response = True
        status_char = None

        for service in client.services:
            if service.uuid.lower() != wanted_service:
                continue
            for char in service.characteristics:
                properties = {p.lower() for p in char.properties}
                if char.uuid.lower() == wanted_read and "notify" in properties:
                    read_char = char
                if wanted_status and char.uuid.lower() == wanted_status and (
                    "notify" in properties or "indicate" in properties
                ):
                    status_char = char
                if char.uuid.lower() == wanted_write:
                    if "write-without-response" in properties:
                        write_char = char
                        write_response = False
                    elif "write" in properties and write_char is None:
                        write_char = char
                        write_response = True

        if read_char is None:
            raise RuntimeError(f"找不到 notify 特征: {wanted_read}")
        if write_char is None:
            raise RuntimeError(f"找不到 write 特征: {wanted_write}")
        self.status_char = status_char
        return read_char, write_char, write_response

    def _on_disconnect(self, _client: Any) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.connection_lost.set)

    def _on_ble_data(self, _handle: Any, data: bytearray) -> None:
        if self.master_fd is None:
            return
        try:
            os.write(self.master_fd, bytes(data))
        except OSError as exc:
            if not self.stop_event.is_set():
                log("WARN", f"BLE -> PTY 写入失败: {exc}")

    def _on_status_data(self, handle: Any, data: bytearray) -> None:
        hex_data = bytes(data).hex()
        log("STATUS", f"{handle} hex={hex_data}")

    async def _pty_to_ble_loop(self) -> None:
        if self.master_fd is None:
            return
        while not self.stop_event.is_set():
            try:
                data = await asyncio.to_thread(os.read, self.master_fd, 4096)
            except asyncio.CancelledError:
                raise
            except OSError as exc:
                if self.stop_event.is_set():
                    return
                log("WARN", f"PTY 读取异常，继续等待: {exc}")
                await asyncio.sleep(0.2)
                continue

            if not data:
                await asyncio.sleep(0.05)
                continue
            await self._send_to_ble(data)

    async def _send_to_ble(self, data: bytes) -> None:
        client = self.client
        write_char = self.write_char
        if not client or not write_char or not self.ble_connected.is_set() or not client.is_connected:
            now = asyncio.get_running_loop().time()
            if now - self._last_no_link_warning > 5:
                log("WARN", "CRT 有数据但 BLE 尚未连接，本段数据丢弃")
                self._last_no_link_warning = now
            return

        chunk_size = max(1, self.settings.chunk_size)
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset : offset + chunk_size]
            try:
                await client.write_gatt_char(
                    write_char,
                    chunk,
                    response=self.write_response,
                )
            except Exception as exc:
                log("ERROR", f"PTY -> BLE 写入失败: {type(exc).__name__}: {exc}")
                self.ble_connected.clear()
                self.connection_lost.set()
                return
            if self.settings.write_delay > 0:
                await asyncio.sleep(self.settings.write_delay)

    async def _disconnect(self) -> None:
        self.ble_connected.clear()
        client = self.client
        read_char = self.read_char
        status_char = self.status_char
        self.client = None
        self.read_char = None
        self.write_char = None
        self.status_char = None
        if client is None:
            return
        try:
            if client.is_connected and read_char is not None:
                await client.stop_notify(read_char)
        except Exception:
            pass
        try:
            if client.is_connected and status_char is not None:
                await client.stop_notify(status_char)
        except Exception:
            pass
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception:
            pass

    async def _wait_or_stop(self, seconds: float) -> None:
        if seconds <= 0:
            return
        try:
            await asyncio.wait_for(self.stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    def _write_state(self, state: str) -> None:
        path = self.settings.state_file
        if not path:
            return
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(f"{state} {stamp}\n")
        except OSError as exc:
            log("WARN", f"写状态文件失败: {exc}")


async def discover_only(settings: Settings) -> int:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        log("ERROR", "当前 Python 没有 bleak")
        return 2

    helper = BlePtyBridge(settings)
    target = await helper._find_target(BleakScanner)
    if target is None:
        return 1

    client = BleakClient(target, timeout=settings.connect_timeout)
    try:
        await client.connect()
        log("CONNECTED", f"{getattr(target, 'name', None)} @ {getattr(target, 'address', '')}")
        for service in client.services:
            print(f"SERVICE {service.uuid}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  CHAR {char.uuid} [{props}]")
        return 0
    finally:
        if client.is_connected:
            await client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WF610 BLE 到持久虚拟串口桥接")
    parser.add_argument(
        "--target-name",
        default=os.getenv("WF610_BLE_NAME", "WF610BLE"),
    )
    parser.add_argument(
        "--target-address",
        default=os.getenv(
            "WF610_BLE_ADDRESS",
            "56864941-4310-3722-B52D-EA59372A16B9",
        ),
    )
    parser.add_argument("--service-uuid", default=os.getenv("WF610_BLE_SERVICE", "fff0"))
    parser.add_argument("--read-uuid", default=os.getenv("WF610_BLE_READ", "fff1"))
    parser.add_argument("--write-uuid", default=os.getenv("WF610_BLE_WRITE", "fff2"))
    parser.add_argument("--status-uuid", default=os.getenv("WF610_BLE_STATUS", "fff3"))
    parser.add_argument("--port", default=os.getenv("WF610_BLE_PORT", "/tmp/ttyWF610BLE"))
    parser.add_argument(
        "--state-file",
        default=os.getenv("WF610_BLE_STATE", "/tmp/wf610-ble-bridge.state"),
    )
    parser.add_argument("--scan-time", type=float, default=10.0)
    parser.add_argument("--reconnect-delay", type=float, default=3.0)
    parser.add_argument("--connect-timeout", type=float, default=15.0)
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=180,
        help="BLE 单次写入字节数；本机实测 MTU 247，默认 180",
    )
    parser.add_argument("--write-delay", type=float, default=0.0)
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="连接后只打印 GATT 服务/特征，不创建 PTY",
    )
    return parser.parse_args()


def make_settings(args: argparse.Namespace) -> Settings:
    return Settings(
        target_name=args.target_name or None,
        target_address=args.target_address or None,
        service_uuid=normalize_uuid(args.service_uuid),
        read_uuid=normalize_uuid(args.read_uuid),
        write_uuid=normalize_uuid(args.write_uuid),
        status_uuid=(normalize_uuid(args.status_uuid) if args.status_uuid else None),
        port_link=args.port,
        scan_timeout=args.scan_time,
        reconnect_delay=args.reconnect_delay,
        connect_timeout=args.connect_timeout,
        chunk_size=args.chunk_size,
        write_delay=args.write_delay,
        state_file=args.state_file,
    )


def main() -> int:
    args = parse_args()
    settings = make_settings(args)
    if args.discover_only:
        try:
            return asyncio.run(discover_only(settings))
        except KeyboardInterrupt:
            return 130

    bridge = BlePtyBridge(settings)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, bridge.request_stop)
        except (NotImplementedError, RuntimeError):
            pass
    try:
        loop.run_until_complete(bridge.run())
    except KeyboardInterrupt:
        bridge.request_stop()
        loop.run_until_complete(asyncio.sleep(0))
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
