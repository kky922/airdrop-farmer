"""
projects/abstract.py — Abstract L2 파밍 모듈

ADD- INFORMATION:
- FDV $3B, 가스비 ~$10, 긴급도 즉시
- abs.xyz XP 적립, 배지 수집 (게임, 소셜, 트레이딩)
- Playwright UI 조작
"""
import asyncio
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from projects.base_project import BaseProject

logger = logging.getLogger(__name__)

ABSTRACT_RPC = "https://api.mainnet.abs.xyz"
ABSTRACT_CHAIN_ID = 2741


class AbstractProject(BaseProject):
    name = "Abstract"
    chain = "abstract"
    category = "L2 게이밍"
    priority = 9
    active = True
    fdv_usd = 3_000_000_000
    urgency = "IMMEDIATE"
    gas_usd = 10

    def _ensure_logs_dir(self) -> Path:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    def _build_shot_path(self, action: str, wallet_address: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(self._ensure_logs_dir() / f"abstract_{action}_{wallet_address[:6]}_{ts}.png")

    def _result(self, success: bool, action: str, xp_earned: int, details: str, **kwargs) -> dict:
        payload = {
            "success": success,
            "action": action,
            "xp_earned": int(xp_earned),
            "details": details,
        }
        payload.update(kwargs)
        return payload

    async def farm(self, wallet_mgr, proxy: dict, behavior) -> dict:
        results = []
        from anti_sybil.browser_manager import BrowserManager
        browser_mgr = BrowserManager(self.config)
        wallets = wallet_mgr.get_all_wallets()

        for i, wallet in enumerate(wallets):
            try:
                browser, context, page = await browser_mgr.get_stealth_browser(
                    wallet.address, proxy
                )
                # XP 액션 순서 랜덤화
                actions = behavior.shuffle_actions(
                    ["xp_earn", "badge_collect", "game_interact", "social_task"],
                    wallet.address
                )
                dry_run = bool(getattr(self, "dry_run", True))
                for action in actions:
                    result = await self._execute_action(page, wallet, action, behavior, dry_run=dry_run)
                    results.append(result)
                    await asyncio.sleep(5)

                await browser.close()
                if i < len(wallets) - 1:
                    await behavior.sleep_between_wallets(i)

            except Exception as e:
                logger.error(f"[Abstract] {wallet.address[:8]} 실패: {e}")
                results.append({"success": False, "error": str(e)})

        await browser_mgr.close_all()
        success = sum(1 for r in results if r.get("success"))
        return {"project": self.name, "success": success, "total": len(results), "results": results}

    async def _execute_action(self, page, wallet, action: str, behavior, dry_run: bool = True) -> dict:
        try:
            if action == "xp_earn":
                return await self._do_xp_earn(page, wallet, behavior, dry_run=dry_run)

            elif action == "badge_collect":
                return await self._do_badge_collect(page, wallet, behavior, dry_run=dry_run)

            elif action == "game_interact":
                return await self._do_game_interact(page, wallet, behavior, dry_run=dry_run)

            elif action == "social_task":
                return await self._do_social_task(page, wallet, behavior, dry_run=dry_run)

            return self._result(False, action, 0, f"미지원 액션: {action}", dry_run=dry_run)
        except Exception as e:
            return self._result(False, action, 0, str(e), dry_run=dry_run)

    async def _do_xp_earn(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        action = "xp_earn"
        started = time.monotonic()
        screenshot_path = self._build_shot_path(action, wallet.address)
        try:
            await page.goto("https://abs.xyz/explore", wait_until="networkidle", timeout=30000)
            await behavior.simulate_reading(page)

            xp_related_count = await page.locator(
                "text=/XP|points|earn/i"
            ).count()
            task_locator = page.locator("button, a, [role='button'], [class*='task'], [class*='card']")
            task_texts = await task_locator.evaluate_all(
                "els => els.map(e => (e.innerText || '').trim()).filter(t => t && t.length < 180)"
            )
            task_texts = task_texts[:20]

            completed_count = await page.locator(
                "text=/completed|done|claimed|finished/i"
            ).count()
            xp_numbers = await page.locator("text=/\\d+\\s*(XP|xp|points)/").all_inner_texts()
            xp_earned = 0
            for txt in xp_numbers:
                digits = "".join(ch for ch in txt if ch.isdigit())
                if digits:
                    xp_earned = max(xp_earned, int(digits))

            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"[Abstract] XP 관련 요소={xp_related_count}, 태스크 샘플={task_texts}")
            details = (
                f"xp_related={xp_related_count}, task_cards={len(task_texts)}, "
                f"completed={completed_count}"
            )
            return self._result(
                True,
                action,
                xp_earned,
                details,
                dry_run=dry_run,
                completed_tasks=completed_count,
                task_cards=task_texts,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )
        except Exception as e:
            return self._result(
                False,
                action,
                0,
                str(e),
                dry_run=dry_run,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )

    async def _do_badge_collect(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        action = "badge_collect"
        started = time.monotonic()
        screenshot_path = self._build_shot_path(action, wallet.address)
        try:
            await page.goto("https://abs.xyz/badges", wait_until="networkidle", timeout=30000)
            await behavior.simulate_reading(page)

            locked_count = await page.locator("text=/locked/i").count()
            unlocked_count = await page.locator("text=/unlocked|claim|collect/i").count()
            collectible = page.locator(
                "button:has-text('Collect'), button:has-text('Claim'), "
                "button:has-text('collect'), button:has-text('claim')"
            )
            collectible_count = await collectible.count()
            clicked = False
            if collectible_count > 0:
                logger.info(f"[Abstract] 수집 가능한 배지 후보 {collectible_count}개")
                try:
                    await collectible.first.click(timeout=4000)
                    clicked = True
                except Exception as click_err:
                    logger.info(f"[Abstract] 배지 클릭 시도 실패: {click_err}")

            await page.screenshot(path=screenshot_path, full_page=True)
            details = (
                f"locked={locked_count}, unlocked={unlocked_count}, "
                f"collectible={collectible_count}, clicked={clicked}"
            )
            return self._result(
                True,
                action,
                collectible_count if clicked else 0,
                details,
                dry_run=dry_run,
                locked_count=locked_count,
                unlocked_count=unlocked_count,
                collectible_count=collectible_count,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )
        except Exception as e:
            return self._result(
                False,
                action,
                0,
                str(e),
                dry_run=dry_run,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )

    async def _do_game_interact(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        action = "game_interact"
        started = time.monotonic()
        screenshot_path = self._build_shot_path(action, wallet.address)
        try:
            await page.goto("https://abs.xyz/games", wait_until="networkidle", timeout=30000)
            await behavior.simulate_reading(page)

            game_links = page.locator("a[href*='/game'], a[href*='/games'], a:has-text('Play')")
            game_count = await game_links.count()
            entered_game = False
            if game_count > 0:
                try:
                    await game_links.first.click(timeout=5000)
                    entered_game = True
                    await behavior.simulate_reading(page)
                except Exception as click_err:
                    logger.info(f"[Abstract] 게임 진입 클릭 실패: {click_err}")

            interaction_sec = random.uniform(30, 120)
            deadline = time.monotonic() + interaction_sec
            hover_count = 0
            while time.monotonic() < deadline:
                y = random.randint(200, 2200)
                await page.evaluate(f"window.scrollTo(0, {y})")
                hoverables = page.locator("button:visible, a:visible")
                if await hoverables.count() > 0:
                    idx = random.randint(0, min(2, await hoverables.count() - 1))
                    try:
                        await hoverables.nth(idx).hover(timeout=2000)
                        hover_count += 1
                    except Exception:
                        pass
                await asyncio.sleep(random.uniform(1.0, 3.0))

            await page.screenshot(path=screenshot_path, full_page=True)
            details = (
                f"games_found={game_count}, entered_first={entered_game}, "
                f"interaction_sec={round(interaction_sec, 1)}, hovers={hover_count}"
            )
            return self._result(
                True,
                action,
                0,
                details,
                dry_run=dry_run,
                games_found=game_count,
                entered_game=entered_game,
                hover_count=hover_count,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )
        except Exception as e:
            return self._result(
                False,
                action,
                0,
                str(e),
                dry_run=dry_run,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )

    async def _do_social_task(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        action = "social_task"
        started = time.monotonic()
        screenshot_path = self._build_shot_path(action, wallet.address)
        visited_url = ""
        try:
            for url in ("https://abs.xyz/social", "https://abs.xyz/quests", "https://abs.xyz/explore"):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    visited_url = url
                    await behavior.simulate_reading(page)
                    break
                except Exception:
                    continue
            if not visited_url:
                raise RuntimeError("소셜/퀘스트 페이지 접속 실패")

            task_candidates = await page.locator(
                "button, a, [role='button'], [class*='task'], [class*='quest']"
            ).evaluate_all(
                "els => els.map(e => (e.innerText || '').trim()).filter(t => t && t.length < 180)"
            )
            actionable = [
                t for t in task_candidates
                if any(k in t.lower() for k in ("follow", "join", "tweet", "share", "discord", "social", "quest"))
            ][:20]
            logger.info(f"[Abstract] 소셜 태스크 후보: {actionable}")

            await page.screenshot(path=screenshot_path, full_page=True)
            details = f"url={visited_url}, social_tasks={len(actionable)}"
            return self._result(
                True,
                action,
                len(actionable),
                details,
                dry_run=dry_run,
                tasks=actionable,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )
        except Exception as e:
            return self._result(
                False,
                action,
                0,
                str(e),
                dry_run=dry_run,
                screenshot_path=screenshot_path,
                elapsed_sec=round(time.monotonic() - started, 3),
            )

    async def farm_single(self, wallet, proxy: dict, behavior) -> dict:
        """단일 지갑 Abstract 파밍 — 시빌 방지."""
        from anti_sybil.browser_manager import BrowserManager
        browser_mgr = BrowserManager(self.config)
        results = []

        try:
            browser, context, page = await browser_mgr.get_stealth_browser(
                wallet.address, proxy
            )
            actions = behavior.shuffle_actions(
                ["xp_earn", "badge_collect", "game_interact", "social_task"],
                wallet.address,
            )
            dry_run = bool(getattr(self, "dry_run", True))
            for action in actions:
                result = await self._execute_action(page, wallet, action, behavior, dry_run=dry_run)
                results.append(result)
                await asyncio.sleep(random.uniform(5, 15))

            await browser.close()
        except Exception as e:
            logger.error(f"[Abstract] {wallet.address[:8]} 실패: {e}")
            results.append({"success": False, "error": str(e)})
        finally:
            await browser_mgr.close_all()

        success = sum(1 for r in results if r.get("success"))
        return {
            "success": success > 0,
            "project": self.name,
            "wallet": wallet.address[:10] + "...",
            "owner": wallet.owner,
            "actions_done": len(results),
            "actions_success": success,
            "results": results,
        }

    async def check_eligibility(self, wallet_address: str) -> bool:
        return True

    async def claim(self, wallet_mgr, wallet_index: int) -> dict:
        return {"success": False, "reason": "미상장 — TGE 이후 클레임 가능"}
