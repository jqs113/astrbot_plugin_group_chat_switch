"""群聊开关 —— 用聊天指令按群开启/关闭 LLM 聊天。

为什么要有它：AstrBot 其实早就支持会话级的 LLM 开关
（sp: scope="umo" / key="session_service_config" / field="llm_enabled"，
 面板在「会话管理」页），但入口只在 WebUI 里。
人在外面、只有手机、刚把机器人拖进一个新群时，那条路走不通。

本插件只做一件事：把同一个字段的写入搬到聊天框里。
写的是官方字段，所以与面板完全同源，不会打架：
- 关掉后 LLM 请求在 agent_request 阶段直接 return，指令照常执行；
- 立刻生效，不需要重载插件或重启。

指令（仅 AstrBot 管理员可用）：
    /开聊              在当前群打开 LLM 聊天
    /关聊              在当前群关闭 LLM 聊天（指令仍可用）
    /聊状态            查看当前群的聊天开关
    /开聊 123456789    按群号远程开关（私聊里也能用）
    /关聊 123456789
    /chat on | off | status [群号]
"""

from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core import sp
from astrbot.core.star.session_llm_manager import SessionServiceManager

PLUGIN_NAME = "astrbot_plugin_group_chat_switch"
CONFIG_KEY = "session_service_config"


async def _read_override(umo: str) -> bool | None:
    """读取该会话是否被显式设置过 llm_enabled；没设置过返回 None。"""
    cfg = await sp.get_async(
        scope="umo",
        scope_id=umo,
        key=CONFIG_KEY,
        default={},
    )
    if not isinstance(cfg, dict):
        return None
    value = cfg.get("llm_enabled")
    return value if isinstance(value, bool) else None


def _tail_args(event: AstrMessageEvent, skip: int = 1) -> list[str]:
    """取指令后面的参数。

    waking_check 已经剥掉了唤醒前缀，所以 message_str 形如
    「开聊 123456789」——第一段是指令名本身，跳过后即参数。
    """
    parts = (event.message_str or "").strip().split()
    return parts[skip:] if len(parts) > skip else []


def _group_umo(event: AstrMessageEvent, group_id: str) -> str | None:
    """按群号拼出会话标识：platform_id:GroupMessage:group_id。"""
    parts = (event.unified_msg_origin or "").split(":")
    if not parts or not parts[0]:
        return None
    return f"{parts[0]}:GroupMessage:{group_id}"


@register(PLUGIN_NAME, "Aqua", "用聊天指令按群开关 LLM 聊天", "1.0.0")
class GroupChatSwitch(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # ------------------------------------------------------------------ 内部
    async def _toggle(self, event: AstrMessageEvent, enabled: bool, args: list[str]):
        if not event.is_admin():
            yield event.plain_result("这操作只有管理员能做。")
            return

        target_umo = event.unified_msg_origin
        label = "本群"
        if args:
            gid = args[0]
            if not gid.isdigit():
                yield event.plain_result("群号要纯数字，比如 /开聊 123456789")
                return
            remote = _group_umo(event, gid)
            if not remote:
                yield event.plain_result("拿不到平台标识，远程开关用不了，请在群里直接发。")
                return
            target_umo, label = remote, f"群 {gid}"

        try:
            await SessionServiceManager.set_llm_status_for_session(
                target_umo,
                enabled,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[group_chat_switch] 写入会话配置失败: {exc!s}")
            yield event.plain_result(f"没写进去：{exc!s}")
            return

        logger.info(
            f"[group_chat_switch] {label} -> llm_enabled={enabled} ({target_umo})",
        )
        if enabled:
            yield event.plain_result(f"{label}的聊天已打开，正常聊就会回。")
        else:
            yield event.plain_result(f"{label}的聊天已关掉，指令还能用。")

    async def _status(self, event: AstrMessageEvent):
        umo = event.unified_msg_origin
        override = await _read_override(umo)
        effective = await SessionServiceManager.is_llm_enabled_for_session(umo)
        if override is None:
            source = "没单独设置过，跟随全局默认"
        else:
            source = "本会话单独设置过：" + ("开" if override else "关")
        yield event.plain_result(
            f"当前聊天：{'开' if effective else '关'}\n{source}\n{umo}",
        )

    # ------------------------------------------------------------------ 指令
    @filter.command("开聊", alias={"群开聊"})
    async def chat_on(self, event: AstrMessageEvent):
        """打开该群的 LLM 聊天。用法：/开聊 或 /开聊 [群号]"""
        async for r in self._toggle(event, True, _tail_args(event)):
            yield r

    @filter.command("关聊", alias={"群关聊"})
    async def chat_off(self, event: AstrMessageEvent):
        """关闭该群的 LLM 聊天（指令仍可用）。用法：/关聊 或 /关聊 [群号]"""
        async for r in self._toggle(event, False, _tail_args(event)):
            yield r

    @filter.command("聊状态", alias={"群聊状态"})
    async def chat_status(self, event: AstrMessageEvent):
        """查看当前会话的聊天开关状态。用法：/聊状态"""
        async for r in self._status(event):
            yield r

    @filter.command("chat")
    async def chat_cmd(self, event: AstrMessageEvent):
        """英文别名：/chat on | off | status [群号]"""
        args = _tail_args(event)
        if not args:
            async for r in self._status(event):
                yield r
            return
        action = args[0].lower()
        rest = args[1:]
        if action in ("on", "open", "1"):
            async for r in self._toggle(event, True, rest):
                yield r
        elif action in ("off", "close", "0"):
            async for r in self._toggle(event, False, rest):
                yield r
        elif action in ("status", "s", "st"):
            async for r in self._status(event):
                yield r
        else:
            yield event.plain_result("用法：/chat on | off | status [群号]")
