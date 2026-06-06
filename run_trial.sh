#!/bin/bash
# ═══════════════════════════════════════════════════
# run_trial.sh — MegaETH 무료 시범 실행 (dry_run)
# ═══════════════════════════════════════════════════
# 💰 비용: $0 (MegaETH 가스 무료 + dry_run 모드)
# 🎯 대상: MegaETH만, 내 지갑 2개
# ═══════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

echo "🧪 ═══════════════════════════════════════"
echo "   MegaETH 무료 시범 테스트"
echo "   비용: \$0 | 모드: dry_run"
echo "═════════════════════════════════════════"
echo ""

# 1. 의존성 체크
echo "📦 [1/4] 의존성 확인..."
pip install -q pyyaml aiohttp web3 2>/dev/null
pip install -q apscheduler 2>/dev/null || echo "   ⚠️ APScheduler 선택사항 (스케줄러 없이도 실행 가능)"
echo "   ✅ 완료"

# 2. 설정 확인
echo ""
echo "⚙️  [2/4] 설정 확인..."
python3 -c "
import yaml, os
from dotenv import load_dotenv
load_dotenv()

cfg = yaml.safe_load(open('config.yaml'))
projects = cfg.get('active_projects', [])
dry = cfg.get('bot', {}).get('dry_run', True)
n_wallets = int(os.getenv('NUM_WALLETS', '0'))

print(f'   활성 프로젝트: {projects}')
print(f'   dry_run: {dry}')
print(f'   지갑 수: {n_wallets}')

if 'MegaETH' not in projects:
    print('   ❌ MegaETH이 활성 프로젝트가 아닙니다!')
    exit(1)
if not dry:
    print('   ⚠️  dry_run=false — 실제 TX가 나갈 수 있습니다!')
print('   ✅ 설정 OK')
"

# 3. 지갑 초기화 테스트
echo ""
echo "💼 [3/4] 지갑 초기화 테스트..."
python3 -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def test():
    from web3_tools.wallet_manager import WalletManager
    import yaml
    cfg = yaml.safe_load(open('config.yaml'))
    wm = WalletManager(cfg)
    wallets = wm.get_all_wallets()
    print(f'   생성된 지갑: {len(wallets)}개')
    for w in wallets:
        label = 'W' if w.owner == 'wife' else f'#{w.index}'
        print(f'   💼 {label}: {w.address[:16]}... ({w.owner})')
    print('   ✅ 지갑 OK')

asyncio.run(test())
"

# 4. MegaETH 파밍 시범 (dry_run)
echo ""
echo "🌾 [4/4] MegaETH 파밍 시범 (dry_run)..."
python3 -c "
import asyncio, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')

from dotenv import load_dotenv
load_dotenv()

async def trial():
    import yaml
    from projects import get_active_projects
    from web3_tools.wallet_manager import WalletManager
    from anti_sybil.behavior_simulator import BehaviorSimulator

    cfg = yaml.safe_load(open('config.yaml'))
    projects = get_active_projects(cfg)
    wm = WalletManager(cfg)
    wallets = wm.get_all_wallets()
    behavior = BehaviorSimulator(cfg)

    print(f'\n   📦 활성 프로젝트: {[p.name for p in projects]}')
    print(f'   💼 지갑: {len(wallets)}개')
    print()

    for project in projects:
        print(f'   ─── {project.name} (가스 \${project.gas_usd}) ───')
        for wallet in wallets:
            label = 'W' if wallet.owner == 'wife' else f'#{wallet.index}'
            print(f'   🔄 {label} 파밍 시작...')
            try:
                result = await project.farm_single(wallet, None, behavior)
                ok = result.get('success', False)
                actions = result.get('actions_done', 0)
                emoji = '✅' if ok else '❌'
                print(f'   {emoji} {label} 완료: {actions}개 액션')
            except Exception as e:
                print(f'   ❌ {label} 실패: {e}')
        print(f'   ✅ {project.name} 완료')

    print()
    print('   🎉 시범 실행 완료!')
    print('   📊 결과는 logs/ 디렉토리의 스크린샷에서 확인')
    print()
    print('   ── 다음 단계 ──')
    print('   1. config.yaml → dry_run: false (실제 실행)')
    print('   2. .env → NUM_WALLETS=5 (지갑 확대)')
    print('   3. config.yaml → 다른 프로젝트 활성화')

asyncio.run(trial())
"

echo ""
echo "✅ ═══════════════════════════════════════"
echo "   시범 테스트 완료!"
echo "   텔레그램으로 결과가 전송되었는지 확인하세요"
echo "═════════════════════════════════════════"