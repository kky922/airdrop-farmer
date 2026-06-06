"""
projects/megaeth.py — MegaETH 파밍 모듈

ADD- INFORMATION:
- FDV $3B, 가스비 완전 무료, TGE 2025-11 완료 (배포 진행 중)
- 최우선 파밍 대상 — 비용 0원이므로 지금 당장 시작
- "The Fluffle" NFT 보유자 최우선 배정
파밍 액션: dApp 상호작용, NFT 민팅, DEX 스왑, 소셜 태스크
"""
import asyncio
import random
import logging
import time
from datetime import datetime
from pathlib import Path
from projects.base_project import BaseProject

logger = logging.getLogger(__name__)

MEGAETH_RPC = "https://rpc.megaeth.com"
MEGAETH_CHAIN_ID = 6342


class MegaETHProject(BaseProject):
    name = "MegaETH"
    chain = "megaeth"
    category = "L2"
    priority = 10
    active = True
    fdv_usd = 3_000_000_000
    urgency = "IMMEDIATE"
    gas_usd = 0  # 완전 무료!

    def _ensure_logs_dir(self) -> Path:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    def _build_shot_path(self, prefix: str, wallet_address: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short = wallet_address[:6]
        return str(self._ensure_logs_dir() / f"{prefix}_{short}_{ts}.png")

    async def farm(self, wallet_mgr, proxy: dict, behavior) -> dict:
        """
        MegaETH 파밍 실행.
        무료 가스 → 매일 최대한 많이 상호작용.
        """
        results = []
        from anti_sybil.browser_manager import BrowserManager
        browser_mgr = BrowserManager(self.config)

        wallets = wallet_mgr.get_all_wallets()
        # 액션 순서 랜덤화 (시빌 방지)
        actions = behavior.shuffle_actions(
            ["dex_swap", "nft_mint", "dapp_interact"],
            wallet_address=wallets[0].address if wallets else "",
        )

        for i, wallet in enumerate(wallets):
            try:
                wallet_proxy = proxy  # 지갑별 프록시는 ProxyManager에서 관리
                browser, context, page = await browser_mgr.get_stealth_browser(
                    wallet.address, wallet_proxy
                )

                dry_run = bool(getattr(self, "dry_run", True))
                for action in actions:
                    result = await self._execute_action(
                        page, wallet, action, behavior, dry_run=dry_run
                    )
                    results.append(result)
                    # 액션 간 딜레이
                    await asyncio.sleep(random.uniform(10, 30))

                await browser.close()

                # 지갑 간 딜레이 (마지막 지갑 제외)
                if i < len(wallets) - 1:
                    await behavior.sleep_between_wallets(i)

            except Exception as e:
                logger.error(f"[MegaETH] 지갑 {wallet.address[:8]} 실패: {e}")
                results.append({"success": False, "error": str(e)})

        await browser_mgr.close_all()
        success = sum(1 for r in results if r.get("success"))
        return {
            "project": self.name,
            "success": success,
            "total": len(results),
            "results": results,
        }

    async def _execute_action(self, page, wallet, action: str, behavior, dry_run: bool = True) -> dict:
        """개별 액션 실행."""
        started = time.monotonic()
        try:
            if action == "dex_swap":
                return await self._do_dex_swap(page, wallet, behavior, dry_run=dry_run)
            elif action == "nft_mint":
                return await self._do_nft_mint(page, wallet, behavior, dry_run=dry_run)
            elif action == "dapp_interact":
                return await self._do_dapp_interact(page, wallet, behavior, dry_run=dry_run)
            return {
                "success": False,
                "action": action,
                "reason": f"미지원 액션: {action}",
                "elapsed_sec": round(time.monotonic() - started, 3),
            }
        except Exception as e:
            return {
                "success": False,
                "action": action,
                "error": str(e),
                "elapsed_sec": round(time.monotonic() - started, 3),
            }

    async def _do_dex_swap(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        """DEX 스왑 페이지 탐색/점검."""
        started = time.monotonic()
        screenshot_path = self._build_shot_path("megaeth_swap", wallet.address)
        target_url = ""
        try:
            for url in ("https://testnet.megaeth.com", "https://app.megaeth.com"):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    target_url = url
                    break
                except Exception:
                    continue
            if not target_url:
                raise RuntimeError("MegaETH DEX 페이지 접속 실패")

            await behavior.simulate_reading(page, min_sec=2, max_sec=6)
            connect_wallet_found = await page.get_by_role("button", name="Connect Wallet").count() > 0
            if connect_wallet_found:
                logger.info("[MegaETH] Connect Wallet 버튼 감지 (수동 연결 필요)")

            swap_button_count = await page.locator(
                "button:has-text('Swap'), button:has-text('swap')"
            ).count()
            input_count = await page.locator("input").count()
            await page.screenshot(path=screenshot_path, full_page=True)

            if not dry_run and swap_button_count > 0:
                await page.locator("button:has-text('Swap'), button:has-text('swap')").first.click(timeout=3000)

            return {
                "success": True,
                "action": "dex_swap",
                "dry_run": dry_run,
                "page_url": target_url,
                "connect_wallet_found": connect_wallet_found,
                "buttons_found": swap_button_count,
                "inputs_found": input_count,
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }
        except Exception as e:
            return {
                "success": False,
                "action": "dex_swap",
                "dry_run": dry_run,
                "error": str(e),
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }

    async def _do_nft_mint(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        """NFT 민팅 요소 탐색."""
        started = time.monotonic()
        screenshot_path = self._build_shot_path("megaeth_nft", wallet.address)
        try:
            await page.goto("https://app.megaeth.com", wait_until="networkidle", timeout=30000)
            await behavior.simulate_reading(page, min_sec=2, max_sec=6)

            selector = (
                "button:has-text('mint'), button:has-text('Mint'), "
                "button:has-text('Free Mint'), button:has-text('free mint'), "
                "button:has-text('claim'), button:has-text('Claim'), "
                "a:has-text('mint'), a:has-text('claim')"
            )
            mint_candidates = page.locator(selector)
            candidate_count = await mint_candidates.count()
            logger.info(f"[MegaETH] NFT 민팅 후보 요소 수: {candidate_count}")

            if not dry_run and candidate_count > 0:
                await mint_candidates.first.click(timeout=3000)

            await page.screenshot(path=screenshot_path, full_page=True)
            return {
                "success": True,
                "action": "nft_mint",
                "dry_run": dry_run,
                "mint_or_claim_found": candidate_count > 0,
                "buttons_found": candidate_count,
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }
        except Exception as e:
            return {
                "success": False,
                "action": "nft_mint",
                "dry_run": dry_run,
                "error": str(e),
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }

    async def _do_dapp_interact(self, page, wallet, behavior, dry_run: bool = True) -> dict:
        """dApp 구조 파악 및 상호작용 대상 수집."""
        started = time.monotonic()
        screenshot_path = self._build_shot_path("megaeth_dapp", wallet.address)
        try:
            await page.goto("https://app.megaeth.com", wait_until="networkidle", timeout=30000)
            await behavior.simulate_reading(page, min_sec=4, max_sec=10)

            page_title = await page.title()
            button_texts = await page.locator("button").evaluate_all(
                "els => els.map(e => (e.innerText || '').trim()).filter(Boolean)"
            )
            link_texts = await page.locator("a").evaluate_all(
                "els => els.map(e => (e.innerText || '').trim()).filter(Boolean)"
            )
            section_texts = await page.locator("h1, h2, h3, section, article, nav").evaluate_all(
                "els => els.map(e => (e.innerText || '').trim()).filter(Boolean).slice(0, 8)"
            )
            interactive_items = (button_texts + link_texts)[:20]
            logger.info(f"[MegaETH] title={page_title}")
            logger.info(f"[MegaETH] 상호작용 요소 샘플: {interactive_items}")
            logger.info(f"[MegaETH] 주요 섹션 샘플: {section_texts}")

            if not dry_run:
                clickable = page.locator("button:visible, a:visible")
                if await clickable.count() > 0:
                    await clickable.first.click(timeout=3000)

            await page.screenshot(path=screenshot_path, full_page=True)
            return {
                "success": True,
                "action": "dapp_interact",
                "dry_run": dry_run,
                "page_title": page_title,
                "buttons_found": len(button_texts),
                "links_found": len(link_texts),
                "interactive_items": interactive_items,
                "sections_preview": section_texts,
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }
        except Exception as e:
            return {
                "success": False,
                "action": "dapp_interact",
                "dry_run": dry_run,
                "error": str(e),
                "screenshot_path": screenshot_path,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }

    async def farm_single(self, wallet, proxy: dict, behavior) -> dict:
        """
        단일 지갑 MegaETH 파밍 — 시빌 방지 (지갑별 독립 실행).
        무료 가스 → 매일 최대한 많이 상호작용.
        """
        from anti_sybil.browser_manager import BrowserManager
        browser_mgr = BrowserManager(self.config)
        results = []

        try:
            browser, context, page = await browser_mgr.get_stealth_browser(
                wallet.address, proxy
            )
            # 액션 순서 랜덤화
            actions = behavior.shuffle_actions(
                ["dex_swap", "nft_mint", "dapp_interact"],
                wallet_address=wallet.address,
            )

            dry_run = bool(getattr(self, "dry_run", True))
            for action in actions:
                result = await self._execute_action(
                    page, wallet, action, behavior, dry_run=dry_run
                )
                results.append(result)
                # 액션 간 딜레이
                await asyncio.sleep(random.uniform(10, 30))

            await browser.close()
        except Exception as e:
            logger.error(f"[MegaETH] 지갑 {wallet.address[:8]} 실패: {e}")
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
        """MegaETH 클레임 자격 확인 (배포 진행 중)."""
        # 배포 진행 중 — 공식 포털에서 확인 필요
        logger.info(f"[MegaETH] 자격 확인: https://megaeth.com (지갑: {wallet_address[:8]}...)")
        return True

    async def claim(self, wallet_mgr, wallet_index: int) -> dict:
        """MegaETH 클레임 — TGE 완료, 포털에서 클레임 가능."""
        return {
            "success": False,
            "manual_required": True,
            "portal": "https://megaeth.com",
            "note": "TGE 2025-11 완료. 공식 포털에서 직접 클레임.",
        }
