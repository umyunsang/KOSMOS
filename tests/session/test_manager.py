# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.session.manager — turn saving, session resume, auto_title."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall
from kosmos.session.manager import SessionManager, auto_title

# ---------------------------------------------------------------------------
# auto_title
# ---------------------------------------------------------------------------


class TestAutoTitle:
    def test_extracts_first_user_message(self) -> None:
        msgs = [
            ChatMessage(role="user", content="오늘 날씨 알려줘"),
            ChatMessage(role="assistant", content="맑습니다"),
        ]
        assert auto_title(msgs) == "오늘 날씨 알려줘"

    def test_truncates_long_message(self) -> None:
        long_text = "A" * 60
        msgs = [ChatMessage(role="user", content=long_text)]
        title = auto_title(msgs)
        assert len(title) <= 51  # 50 chars + ellipsis
        assert title.endswith("…")

    def test_skips_non_user_messages(self) -> None:
        msgs = [
            ChatMessage(role="assistant", content="안녕"),
            ChatMessage(role="user", content="첫 번째 질문"),
        ]
        assert auto_title(msgs) == "첫 번째 질문"

    def test_returns_untitled_when_no_user_messages(self) -> None:
        msgs = [ChatMessage(role="assistant", content="hello")]
        assert auto_title(msgs) == "Untitled"

    def test_empty_list(self) -> None:
        assert auto_title([]) == "Untitled"

    def test_strips_whitespace_and_newlines(self) -> None:
        msgs = [ChatMessage(role="user", content="  질문\n이어서  ")]
        assert auto_title(msgs) == "질문 이어서"

    def test_exactly_50_chars_no_ellipsis(self) -> None:
        content = "가" * 50
        msgs = [ChatMessage(role="user", content=content)]
        title = auto_title(msgs)
        assert "…" not in title
        assert len(title) == 50


# ---------------------------------------------------------------------------
# SessionManager — new_session / resume_session
# ---------------------------------------------------------------------------


class TestSessionManagerLifecycle:
    @pytest.mark.asyncio
    async def test_new_session_creates_metadata(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        meta = await manager.new_session()
        assert meta.session_id is not None
        assert manager.session_id == meta.session_id

    @pytest.mark.asyncio
    async def test_new_session_file_exists(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        meta = await manager.new_session()
        assert (tmp_path / f"{meta.session_id}.jsonl").exists()

    @pytest.mark.asyncio
    async def test_resume_empty_session(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        meta = await manager.new_session()
        messages = await manager.resume_session(meta.session_id)
        # New session has no messages yet
        assert messages == []

    @pytest.mark.asyncio
    async def test_resume_nonexistent_session_raises(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            await manager.resume_session("ghost-session-id")


# ---------------------------------------------------------------------------
# SessionManager — save_turn
# ---------------------------------------------------------------------------


class TestSessionManagerSaveTurn:
    @pytest.mark.asyncio
    async def test_save_turn_persists_messages(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        await manager.new_session()

        user_msg = ChatMessage(role="user", content="오늘 날씨 어때요?")
        assistant_msg = ChatMessage(role="assistant", content="맑습니다.")
        await manager.save_turn(user_msg=user_msg, assistant_msg=assistant_msg)

        messages = await manager.resume_session(manager.session_id)  # type: ignore[arg-type]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "오늘 날씨 어때요?"
        assert messages[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_save_turn_with_tool_calls(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        await manager.new_session()

        user_msg = ChatMessage(role="user", content="서울 날씨 조회")
        tool_calls = [
            ToolCall(id="call_001", function=FunctionCall(name="weather", arguments="{}"))
        ]
        assistant_msg = ChatMessage(
            role="assistant",
            content=None,
            tool_calls=tool_calls,
        )
        # Should not raise
        await manager.save_turn(
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            tool_calls=tool_calls,
        )

    @pytest.mark.asyncio
    async def test_save_turn_without_active_session_raises(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        # No new_session() called
        user_msg = ChatMessage(role="user", content="hello")
        assistant_msg = ChatMessage(role="assistant", content="world")
        with pytest.raises(RuntimeError, match="No active session"):
            await manager.save_turn(user_msg=user_msg, assistant_msg=assistant_msg)

    @pytest.mark.asyncio
    async def test_multiple_turns_accumulate(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        await manager.new_session()

        for i in range(3):
            await manager.save_turn(
                user_msg=ChatMessage(role="user", content=f"질문 {i}"),
                assistant_msg=ChatMessage(role="assistant", content=f"답변 {i}"),
            )

        messages = await manager.resume_session(manager.session_id)  # type: ignore[arg-type]
        assert len(messages) == 6  # 3 user + 3 assistant


# ---------------------------------------------------------------------------
# SessionManager — set_title
# ---------------------------------------------------------------------------


class TestSessionManagerSetTitle:
    @pytest.mark.asyncio
    async def test_set_title_persists(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        await manager.new_session()

        messages = [ChatMessage(role="user", content="제목이 될 첫 번째 메시지")]
        await manager.set_title(messages)

        assert manager.metadata is not None
        assert manager.metadata.title == "제목이 될 첫 번째 메시지"

    @pytest.mark.asyncio
    async def test_set_title_noop_when_already_set(self, tmp_path: Path) -> None:
        from datetime import datetime  # noqa: PLC0415

        from kosmos.session.models import SessionMetadata  # noqa: PLC0415
        from kosmos.session.store import update_session_metadata  # noqa: PLC0415

        manager = SessionManager(session_dir=tmp_path)
        meta = await manager.new_session()

        # Manually set a title via store
        existing_meta = SessionMetadata(
            session_id=meta.session_id,
            created_at=meta.created_at,
            updated_at=datetime.now(UTC),
            title="기존 제목",
        )
        await update_session_metadata(existing_meta, session_dir=tmp_path)
        # Reload into manager
        manager._metadata = existing_meta

        # set_title should be a no-op since title is already set
        messages = [ChatMessage(role="user", content="다른 메시지")]
        await manager.set_title(messages)
        assert manager.metadata.title == "기존 제목"


# ---------------------------------------------------------------------------
# SessionManager — branch_session
# ---------------------------------------------------------------------------


class TestSessionManagerBranching:
    @pytest.mark.asyncio
    async def test_branch_creates_new_session(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        parent_meta = await manager.new_session()
        parent_id = parent_meta.session_id

        messages = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="world"),
        ]
        branch_meta = await manager.branch_session(messages)

        assert branch_meta.session_id != parent_id
        assert branch_meta.parent_session_id == parent_id

    @pytest.mark.asyncio
    async def test_branch_carries_over_messages(self, tmp_path: Path) -> None:
        manager = SessionManager(session_dir=tmp_path)
        await manager.new_session()

        messages = [
            ChatMessage(role="user", content="분기 전 메시지"),
            ChatMessage(role="assistant", content="응답"),
        ]
        branch_meta = await manager.branch_session(messages)
        session_id = branch_meta.session_id

        resumed = await manager.resume_session(session_id)
        assert len(resumed) == 2
        assert resumed[0].content == "분기 전 메시지"
