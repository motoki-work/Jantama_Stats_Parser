# 雀魂牌譜解析スクリプト（雀魂JSON構造に対応・CPU席も集計・副露/カン回数集計）

import os
import json
import csv
from collections import defaultdict

def process_directory(directory):
    all_stats = defaultdict(lambda: {
        "total_kyoku": 0, "furo_kyoku": 0, "agari_kyoku": 0, "furo_agari_kyoku": 0,
        "chi": 0, "pon": 0, "daiminkan": 0, "kakan": 0, "ankan": 0
    })
    id2name = {}
    hanchan_counter = defaultdict(int)  # 追加: 半荘数カウンタ
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json') or file.endswith('.txt'):
                file_path = os.path.join(root, file)
                print(f"[DEBUG] Processing {file_path}")
                # ユーザー名を抽出
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
                for acc in data['head']['accounts']:
                    id2name[acc['account_id']] = acc.get('nickname', '')
                    # この半荘に登場したIDを記録
                    file_ids = set()
                    file_ids.add(acc['account_id'])
                stats = process_file(file_path)
                for aid, s in stats.items():
                    for key in all_stats[aid]:
                        all_stats[aid][key] += s[key]
                    file_ids.add(aid)  # CPUも含める
                # ファイルに登場した全IDの半荘数を+1
                for aid in file_ids:
                    hanchan_counter[aid] += 1

    # 合算結果を1ファイルに出力
    with open("furo_summary.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "アカウントID", "アカウント名", "半荘数", "参加局数", "副露局数", "副露率", "和了局数", "副露和了局数", "副露和了率",
            "チー回数", "ポン回数", "大明槓回数", "加槓回数", "暗槓回数"
        ])
        for aid, s in all_stats.items():
            # アカウント名（なければ"NPCx"表記）
            name = id2name.get(aid, aid if str(aid).startswith('npc_') else '')
            total = s["total_kyoku"]
            furo = s["furo_kyoku"]
            agari = s["agari_kyoku"]
            furo_agari = s["furo_agari_kyoku"]
            furo_rate = furo / total if total else 0
            furo_agari_rate = furo_agari / agari if agari else 0
            writer.writerow([
                aid, name, hanchan_counter.get(aid, 0), total, furo, f"{furo_rate:.2%}", agari, furo_agari, f"{furo_agari_rate:.2%}",
                s["chi"], s["pon"], s["daiminkan"], s["kakan"], s["ankan"]
            ])

def process_file(file_path):
    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)

    seat2id = {}
    for acc in data['head']['accounts']:
        seat2id[acc['seat']] = acc['account_id']

    # actions配列から未知のseat（CPU等）も拾う
    for act in data['data']['data']['actions']:
        seat = None
        if "result" in act and "data" in act["result"] and "seat" in act["result"]["data"]:
            seat = act["result"]["data"]["seat"]
        if seat is not None and seat not in seat2id:
            seat2id[seat] = f"npc_{seat}"

    kyoku_results = []
    curr_kyoku = None
    kyoku_cnt = -1

    furo_counter = defaultdict(lambda: {
        "chi": 0, "pon": 0, "daiminkan": 0, "kakan": 0, "ankan": 0
    })

    for act in data['data']['data']['actions']:
        if act.get("result", {}).get("name") == ".lq.RecordNewRound":
            curr_kyoku = {seat: {"furo": False, "agari": False} for seat in seat2id}
            kyoku_results.append(curr_kyoku)
            kyoku_cnt += 1

        # チー/ポン/大明槓
        if act.get("result", {}).get("name") == ".lq.RecordChiPengGang":
            chi_peng_gang_type = act["result"]["data"].get("type", 0)
            seat = act["result"]["data"]["seat"]
            acc_id = seat2id[seat]
            if chi_peng_gang_type == 0:
                furo_counter[acc_id]["chi"] += 1
            elif chi_peng_gang_type == 1:
                furo_counter[acc_id]["pon"] += 1
            elif chi_peng_gang_type == 2:
                furo_counter[acc_id]["daiminkan"] += 1

            # 副露判定はチー/ポン/大明槓のみ
            if chi_peng_gang_type in {0, 1, 2}:
                if curr_kyoku and seat in curr_kyoku:
                    curr_kyoku[seat]["furo"] = True

        # 加槓/暗槓
        if act.get("result", {}).get("name") == ".lq.RecordAnGangAddGang":
            an_gang_type = act["result"]["data"].get("type", 0)
            seat = act["result"]["data"]["seat"]
            acc_id = seat2id[seat]
            if an_gang_type == 2:
                furo_counter[acc_id]["kakan"] += 1
            elif an_gang_type == 3:
                furo_counter[acc_id]["ankan"] += 1

        if act.get("result", {}).get("name") == ".lq.RecordHule":
            for h in act["result"]["data"]["hules"]:
                seat = h["seat"]
                if curr_kyoku and seat in curr_kyoku:
                    curr_kyoku[seat]["agari"] = True

    stats = defaultdict(lambda: {
        "total_kyoku": 0, "furo_kyoku": 0, "agari_kyoku": 0, "furo_agari_kyoku": 0,
        "chi": 0, "pon": 0, "daiminkan": 0, "kakan": 0, "ankan": 0
    })
    for kyoku in kyoku_results:
        for seat, info in kyoku.items():
            aid = seat2id[seat]
            stats[aid]["total_kyoku"] += 1
            if info["furo"]:
                stats[aid]["furo_kyoku"] += 1
            if info["agari"]:
                stats[aid]["agari_kyoku"] += 1
                if info["furo"]:
                    stats[aid]["furo_agari_kyoku"] += 1

    for aid in stats:
        for key in ["chi", "pon", "daiminkan", "kakan", "ankan"]:
            stats[aid][key] = furo_counter[aid][key]

    return stats

if __name__ == "__main__":
    process_directory('./paifu_txt')

