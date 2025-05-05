import os
import json
import pandas as pd
from collections import defaultdict, Counter

# 雀魂の役IDと名称対応テーブル
yaku_id_to_name = {
    1: "門前清自摸和", 2: "立直", 3: "槍槓", 4: "嶺上開花", 5: "海底摸月", 6: "河底撈魚",
    7: "役牌白", 8: "役牌發", 9: "役牌中", 10: "役牌:自風牌", 11: "役牌:場風牌",
    12: "断幺九", 13: "一盃口", 14: "平和", 15: "混全帯幺九", 16: "一気通貫", 17: "三色同順",
    18: "ダブル立直", 19: "三色同刻", 20: "三槓子", 21: "対々和", 22: "三暗刻", 23: "小三元",
    24: "混老頭", 25: "七対子", 26: "純全帯幺九", 27: "混一色", 28: "二盃口", 29: "清一色",
    30: "一発", 31: "ドラ", 32: "赤ドラ", 33: "裏ドラ", 34: "抜きドラ", 35: "天和", 36: "地和",
    37: "大三元", 38: "四暗刻", 39: "字一色", 40: "緑一色", 41: "清老頭", 42: "国士無双",
    43: "小四喜", 44: "四槓子", 45: "九蓮宝燈", 46: "八連荘", 47: "純正九蓮宝燈", 48: "四暗刻単騎",
    49: "国士無双十三面待ち", 50: "大四喜"
}

temp_kui_sagari_ids = {15, 16, 17, 26, 27, 29}

def process_directory(directory):
    agari_counter = defaultdict(list)
    agari_point_summary = []
    uid_to_name = {}
    agari_count = Counter()
    houju_count = Counter()
    houju_kyoku_count = Counter()
    houju_point_loss = Counter()
    agari_point_gain = Counter()
    menzen_count = Counter()
    reach_count = Counter()
    total_kyoku = 0
    hanchan_results = []

    kyoku_participation_count = Counter()

  
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    paifu_data = json.load(f)

                seat_to_uid = {
                    p["seat"]: str(p["account_id"]) if "account_id" in p else f"npc_{p['seat']}"
                    for p in paifu_data["head"]["accounts"]
                }
                seat_to_name = {p["seat"]: p.get("nickname", f"NPC{p['seat']}") for p in paifu_data["head"]["accounts"]}
                for seat, uid in seat_to_uid.items():
                    uid_to_name[uid] = seat_to_name.get(seat, f"NPC{seat}")

                # NPC補完
                if "result" in paifu_data["head"] and "players" in paifu_data["head"]["result"]:
                    for p in paifu_data["head"]["result"]["players"]:
                        seat = p.get("seat")
                        if seat not in seat_to_uid:
                            uid = f"npc_{seat}"
                            name = f"NPC{seat}"
                            seat_to_uid[seat] = uid
                            uid_to_name[uid] = name

                actions = paifu_data["data"]["data"].get("actions", [])
                last_actor_seat = None
                for action in actions:
                    actor = action.get("actor")
                    if actor is not None:
                        last_actor_seat = actor
                    if action.get("type") == 1 and isinstance(action.get("result"), dict):
                        result_name = action["result"].get("name")
                        if result_name == ".lq.RecordNewRound":
                            for seat in seat_to_uid:
                                uid = seat_to_uid[seat]
                                kyoku_participation_count[uid] += 1
                        data = action["result"].get("data", {})

                        # 流局発生　流し満貫チェック
                        if result_name == ".lq.RecordNoTile":
                            liujumanguan_flags = data.get("liujumanguan", [])
                            for seat, flag in enumerate(liujumanguan_flags):
                                if flag:
                                    uid = seat_to_uid.get(seat, f"npc_{seat}")
                                    uid_to_name[uid] = seat_to_name.get(seat, f"NPC{seat}")
                                    agari_point_summary.append({
                                        "アカウントID": uid,
                                        "ユーザー名": uid_to_name[uid],
                                        "翻数": 5,
                                        "得点変動": 8000,
                                        "アガリ種別": "流し満貫",
                                        "副露数": 0,
                                        "放銃者ID": "N/A",
                                        "放銃者名": "N/A"
                                    })
                                    agari_count[uid] += 1
                                    agari_point_gain[uid] += 8000

                        # アガリ発生なので集計していく
                        if result_name == ".lq.RecordHule":
                            # 各プレイヤーの局参加数をカウント
                            for seat in seat_to_uid:
                                uid = seat_to_uid[seat]
                                kyoku_participation_count[uid] += 1
                            # 各プレイヤーの局参加数をカウント
                            for seat in seat_to_uid:
                                uid = seat_to_uid[seat]
                                kyoku_participation_count[uid] += 1
                            
                            if result_name == ".lq.RecordHule":
                                total_kyoku += 1
                                hules = data.get("hules", [])
                            delta_scores = data.get("delta_scores", [])

                            for hule in hules:
                                actor_seat = hule.get("seat")
                                actor_uid = seat_to_uid.get(actor_seat, f"npc_{actor_seat}")
                                menqing = hule.get("menqing", True)
                                ming_count = len(hule.get("ming", [])) if isinstance(hule.get("ming"), list) else 0
                                total_han = 0

                                for fan in hule.get("fans", []):
                                    if isinstance(fan, dict) and fan.get("id") is not None:
                                        fan_id = int(fan["id"])
                                        fan_name = yaku_id_to_name.get(fan_id, f"不明ID:{fan_id}")
                                        fan_val = fan.get("val", 0)
                                        kui_sagari = "あり" if fan_id in temp_kui_sagari_ids and ming_count > 0 else "なし"
                                        if fan_name == "裏ドラ" and fan_val == 0:
                                            continue
                                        if fan_id == 1:
                                            menzen_count[actor_uid] += 1
                                        if fan_id == 2:
                                            reach_count[actor_uid] += 1
                                        if kui_sagari == "あり":
                                            fan_name = fan_name + "[食下り]"
                                        agari_counter[actor_uid].append((fan_id, fan_name, fan_val, kui_sagari, "あり" if menqing else "なし", ming_count))
                                        total_han += fan_val

                                agari_type = "ツモ" if hule.get("zimo") else "ロン"
                                point_delta = delta_scores[actor_seat] if 0 <= actor_seat < len(delta_scores) else 0

                                if not hule.get("zimo"):
                                    target_seat = None
                                    if delta_scores:
                                        for seat_idx, delta in enumerate(delta_scores):
                                            if delta < 0 and seat_idx != actor_seat:
                                                target_seat = seat_idx
                                                break
                                else:
                                    target_seat = None
                                if target_seat is not None:
                                    target_uid = seat_to_uid.get(target_seat)
                                    if target_uid is None:
                                        target_uid = f"npc_{target_seat}"
                                        uid_to_name[target_uid] = f"NPC{target_seat}"
                                else:
                                    target_uid = "N/A"
                                target_name = uid_to_name.get(target_uid, "N/A")
                                agari_point_summary.append({
                                    "アカウントID": actor_uid,
                                    "ユーザー名": uid_to_name.get(actor_uid, f"NPC{actor_seat}"),
                                    "翻数": total_han,
                                    "得点変動": point_delta,
                                    "アガリ種別": agari_type,
                                    "副露数": ming_count,
                                    "放銃者ID": target_uid,
                                    "放銃者名": target_name
                                })
                                agari_count[actor_uid] += 1
                                agari_point_gain[actor_uid] += point_delta

                            if delta_scores:
                                for seat_idx, score in enumerate(delta_scores):
                                    if score < 0:
                                        houju_uid = seat_to_uid.get(seat_idx)
                                        if houju_uid:
                                            houju_count[houju_uid] += 1
                                            houju_kyoku_count[houju_uid] += 1
                                            houju_point_loss[houju_uid] += abs(score)

                if "result" in paifu_data["head"] and "players" in paifu_data["head"]["result"]:
                    temp_hanchan = []
                    for p in paifu_data["head"]["result"]["players"]:
                        seat = p.get("seat")
                        uid = seat_to_uid.get(seat, f"npc_{seat}")
                        temp_hanchan.append({
                            "アカウントID": uid,
                            "ユーザー名": uid_to_name.get(uid, f"NPC{seat}"),
                            "得点": p.get("part_point_1", 0)
                        })
                    temp_hanchan_sorted = sorted(temp_hanchan, key=lambda x: x["得点"], reverse=True)
                    for idx, player in enumerate(temp_hanchan_sorted, 1):
                        player["順位"] = idx
                    hanchan_results.extend(temp_hanchan_sorted)

            except Exception as e:
                print(f"[ERROR] {filename}: {e}")

    return agari_counter, agari_point_summary, uid_to_name, agari_count, houju_count, houju_kyoku_count, menzen_count, reach_count, houju_point_loss, agari_point_gain, total_kyoku, hanchan_results, kyoku_participation_count

if __name__ == "__main__":
    target_dir = "./paifu_txt"
    agari_counter, agari_point_summary, uid_to_name, agari_count, houju_count, houju_kyoku_count, menzen_count, reach_count, houju_point_loss, agari_point_gain, total_kyoku, hanchan_results, kyoku_participation_count = process_directory(target_dir)

    agari_rows = []
    for uid, yakus in agari_counter.items():
        for (fan_id, yaku, val, kui_sagari, menqing_flag, ming_count) in yakus:
            agari_rows.append({
                "アカウントID": int(uid) if str(uid).isdigit() else uid,
                "ユーザー名": uid_to_name.get(uid, f"NPC"),
                "役ID": fan_id,
                "役名": yaku,
                "翻数": val,
                "食い下がり": kui_sagari,
                "面前": menqing_flag,
                "副露数": ming_count
            })
    pd.DataFrame(agari_rows).to_csv("agari_summary.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(agari_point_summary).to_csv("agari_point_summary.csv", index=False, encoding="utf-8-sig")

    rate_rows = []
    hanchan_count = Counter()
    for h in hanchan_results:
        hanchan_count[h["アカウントID"]] += 1

    for uid in uid_to_name:
        rate_rows.append({
            "アカウントID": str(uid) if str(uid).isdigit() else uid,
            "ユーザー名": uid_to_name[uid],
            "和了回数": agari_count.get(uid, 0),
            "放銃回数": houju_kyoku_count.get(uid, 0),
            "門前清自摸和回数": menzen_count.get(uid, 0),
            "立直回数": reach_count.get(uid, 0),
            "和了得点": agari_point_gain.get(uid, 0),
            "ツモ回数": sum(1 for x in agari_point_summary if x["アカウントID"] == uid and x["アガリ種別"] == "ツモ"),
            "和了率/局": round(agari_count.get(uid, 0) / kyoku_participation_count.get(uid, 1), 4),
            "立直率/局": round(reach_count.get(uid, 0) / kyoku_participation_count.get(uid, 1), 4),
            "ツモ率/和了": round(
                sum(1 for x in agari_point_summary if x["アカウントID"] == uid and x["アガリ種別"] == "ツモ")
                / agari_count.get(uid, 1), 4),
            "放銃失点": round(houju_point_loss.get(uid, 0), 0),
            "局数": kyoku_participation_count.get(uid, 0),
            "半荘数": hanchan_count.get(uid, 0)
        })

    pd.DataFrame(rate_rows).sort_values(by="アカウントID").to_csv("agari_houju_rate.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(hanchan_results).to_csv("hanchan_summary.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([
        {"アカウントID": str(uid), "ユーザー名": name}
        for uid, name in uid_to_name.items()
    ]).sort_values(by="アカウントID").to_csv("player_roster.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([
        {"総局数": total_kyoku, "総半荘数": len(hanchan_results) // 4}
    ]).to_csv("taikai_results.csv", index=False, encoding="utf-8-sig")

