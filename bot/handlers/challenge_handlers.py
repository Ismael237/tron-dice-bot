from __future__ import annotations

from math import ceil
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards import main_reply_keyboard, challenges_list_inline_keyboard
from bot.messages import msg_challenges_page, msg_not_registered_prompt_start
from services.user_service import UserService
from services.challenge_service import ChallengeService

_PAGE_SIZE = 5


async def handle_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry command to show active challenges and user progress."""
    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return

    svc = ChallengeService()
    items = svc.list_active_for_user(user.id)
    total = len(items)
    total_pages = max(1, ceil(total / _PAGE_SIZE))
    page = 1
    slice_rows = items[0:_PAGE_SIZE]

    text = msg_challenges_page(slice_rows, page, total_pages)
    await update.message.reply_markdown_v2(
        text, reply_markup=challenges_list_inline_keyboard(slice_rows, page, total_pages)
    )


async def handle_challenges_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback handling for challenges pagination and claim actions."""
    query = update.callback_query
    if not query:
        return
    data = (query.data or "").strip()

    user = UserService.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await query.answer()
        await query.message.reply_markdown_v2(
            msg_not_registered_prompt_start(), reply_markup=main_reply_keyboard()
        )
        return

    async def _edit(text: str, reply_markup=None):
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_markdown_v2(text, reply_markup=reply_markup)

    svc = ChallengeService()

    # Pagination: chal_page_{n}
    if data.startswith("chal_page_"):
        try:
            page = max(1, int(data.split("chal_page_")[-1]))
        except Exception:
            page = 1
        items = svc.list_active_for_user(user.id)
        total = len(items)
        total_pages = max(1, ceil(total / _PAGE_SIZE))
        start = (page - 1) * _PAGE_SIZE
        end = start + _PAGE_SIZE
        slice_rows = items[start:end]
        text = msg_challenges_page(slice_rows, page, total_pages)
        await _edit(text, reply_markup=challenges_list_inline_keyboard(slice_rows, page, total_pages))
        await query.answer()
        return

    # Claim: chal_claim_{id}
    if data.startswith("chal_claim_"):
        try:
            cid = int(data.split("chal_claim_")[-1])
        except Exception:
            cid = None
        if cid is None:
            await query.answer("Invalid challenge id", show_alert=True)
            return
        ok, msg = svc.claim_reward(user.id, cid)
        await query.answer(msg, show_alert=not ok)
        # Refresh current page view by re-fetching and showing page 1 (simple approach)
        items = svc.list_active_for_user(user.id)
        total = len(items)
        total_pages = max(1, ceil(total / _PAGE_SIZE))
        page = 1
        slice_rows = items[0:_PAGE_SIZE]
        text = msg_challenges_page(slice_rows, page, total_pages)
        await _edit(text, reply_markup=challenges_list_inline_keyboard(slice_rows, page, total_pages))
        return
