from __future__ import annotations
import os,re,html,asyncio,difflib,logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from vika_engine.prediction import PredictionEngine, HistoricalPlayerMissingError
from vika_engine.providers.livetennis import LiveTennisProvider
from vika_engine.prediction_journal import PredictionJournal
from vika_engine.model_health import ModelHealth
from vika_engine.auto_live import extract_odds, signal_from_live
from vika_engine.auto_live_report import AutoLiveReport
from vika_engine.live_markets import market_candidates
from vika_engine.odds_provider import OddsProvider
from dotenv import load_dotenv
from vika_dialogue import RESPONSES
load_dotenv()
logging.basicConfig(level=logging.INFO); log=logging.getLogger('vika')

SURFACES={'hard':'Hard','хард':'Hard','clay':'Clay','грунт':'Clay','grass':'Grass','трава':'Grass','indoor':'Hard','зал':'Hard'}
ALIASES={'соболенко':'aryna sabalenka','сабаленко':'aryna sabalenka','пегула':'jessica pegula','гауфф':'coco gauff','рыбакина':'elena rybakina','швёнтек':'iga swiatek','свитолина':'elina svitolina','андрееску':'bianca andreescu'}
engine=PredictionEngine(); provider=LiveTennisProvider(); odds_provider=OddsProvider(); journal=PredictionJournal(); auto_report=AutoLiveReport()
WATCH_TASKS={}; MONITOR_TASK=None; CHATS=set(); AUTO_ENABLED=set(); LAST_SIGNALS={}; LAST_DAILY={}


def _dialog(key, default=""):
    import random
    vals=RESPONSES.get(key) or ([default] if default else [])
    return random.choice(vals) if vals else default

def esc(x): return html.escape(str(x))
def simulations_fmt(x): return f'{int(x):,}'.replace(',', ' ')
def player(name): return engine.state.get(name)

def obj_name(m,side):
    p=getattr(m,side,None); return getattr(p,'name',None) if p is not None else None

def obj_id(m): return str(getattr(m,'id',''))
def frame_of(m):
    if hasattr(m,'model_dump'):
        try:return m.model_dump()
        except Exception:pass
    return getattr(m,'__dict__',{}) or {}

def normalize_name(s):
    s=str(s or '').lower().strip(); s=re.sub(r'[^a-zа-яё0-9 ]',' ',s); s=re.sub(r'\s+',' ',s)
    return ALIASES.get(s,s)

def name_score(query,candidate):
    q=normalize_name(query); c=normalize_name(candidate)
    if q==c:return 1
    if q in c or c in q:return .92
    qt,ct=q.split(),c.split()
    if qt and ct and qt[-1]==ct[-1]:return .88
    return difflib.SequenceMatcher(None,q,c).ratio()

def resolve_fixture_pair(p1,p2):
    if not provider.available:return None
    try: rows=provider.current_day()
    except Exception:return None
    best=None; score=0
    for m in rows:
        a,b=obj_name(m,'p1'),obj_name(m,'p2')
        if not a or not b:continue
        s=max(name_score(p1,a)+name_score(p2,b),name_score(p1,b)+name_score(p2,a))
        if s>score:score=s;best=m
    return best if score>=1.35 else None

def parse_match(text):
    t=re.sub(r'\b(против|с|vs|v|—|–)\b',';',text,flags=re.I)
    surface='Hard'
    for k,v in SURFACES.items():
        if re.search(rf'(^|\s|;){re.escape(k)}($|\s|;)',t,re.I):surface=v;t=re.sub(re.escape(k),'',t,flags=re.I)
    parts=[x.strip() for x in t.split(';') if x.strip()]
    if len(parts)<2:
        w=t.split()
        if len(w)==2:parts=w
        elif len(w)>=4:parts=[' '.join(w[:len(w)//2]),' '.join(w[len(w)//2:])]
    return (parts[0],parts[1],surface) if len(parts)>=2 else (None,None,surface)

def canonical_pair(p1,p2):
    m=resolve_fixture_pair(p1,p2)
    return (obj_name(m,'p1'),obj_name(m,'p2'),m) if m else (normalize_name(p1),normalize_name(p2),None)


def menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton('📅 Прогнозы на сегодня',callback_data='day'),InlineKeyboardButton('🔴 Что в лайве?',callback_data='live')],[InlineKeyboardButton('🤖 Авто-режим: ВКЛ',callback_data='auto_on'),InlineKeyboardButton('⛔ Авто-режим: ВЫКЛ',callback_data='auto_off')],[InlineKeyboardButton('ℹ️ Статус Vika',callback_data='status')]])

async def start(update,context):
    chat=update.effective_chat.id; CHATS.add(chat); AUTO_ENABLED.add(chat)
    await update.message.reply_text('Привет! Я Vika 🎾\n\nМогу сама следить за теннисом: дать карту дня, посмотреть LIVE и прислать сигнал, когда модель увидит подходящий момент.\n\nНичего запоминать не надо — просто пиши как человеку, а я разберусь.\n\nНапример: «что сегодня», «что в лайве», «дай Соболенко Пегула», «включи авто».\n\n🤖 Автомониторинг включён.',reply_markup=menu())

async def help_cmd(update,context): await start(update,context)

async def predict_match_text(update,text):
    p1,p2,surface=parse_match(text)
    if not p1 or not p2:return await update.message.reply_text('Я поняла не всё 🙂 Напиши, например: «Соболенко Пегула хард»')
    p1c,p2c,m=canonical_pair(p1,p2)
    try:r=engine.predict(p1c,p2c,surface,3,simulations=100000)
    except Exception as e:return await update.message.reply_text(f'❌ {esc(e)}',parse_mode=ParseMode.HTML)
    r['p1']=p1c;r['p2']=p2c;r['surface']=surface;journal.log(r)
    msg=(f'🎾 <b>{esc(r["features"]["p1_name"])} — {esc(r["features"]["p2_name"])}</b>\nПокрытие: {surface}\n\n<b>Победа</b>\n• {esc(r["features"]["p1_name"])}: <b>{r["p1_win"]*100:.1f}%</b>\n• {esc(r["features"]["p2_name"])}: <b>{r["p2_win"]*100:.1f}%</b>\n\nФорма Δ: {r["features"]["form_diff"]:+.3f} | Elo Δ: {r["features"]["surface_elo_diff"]:+.1f}\nУсталость Δ: {r["features"]["fatigue_diff"]:+.0f} мин | H2H: {r["features"]["h2h_matches"]}\nОжидаемый тотал: {r["expected_total"]:.1f} | Фора: {r["expected_diff"]:+.1f}\nConfidence: {r["confidence"]*100:.0f}% | Data: {r["data_quality"]*100:.0f}%')
    await update.message.reply_text(msg,parse_mode=ParseMode.HTML)

async def predict_cmd(update,context): await predict_match_text(update,' '.join(context.args))

def _build_day_report(provider_obj, engine_obj):
    if not provider_obj.available:
        return ('❌ Live Tennis API не настроен.', 1)
    try:
        rows=provider_obj.current_day()
    except Exception as e:
        return (f'❌ API: {esc(e)}', 1)
    out=['📅 <b>VIKA — ТЕННИС НА СЕГОДНЯ</b>']; ok=0; missing=0; failed=0
    for m in rows:
        a,b=obj_name(m,'p1'),obj_name(m,'p2')
        if not a or not b: continue
        surface=str(getattr(m,'surface',None) or 'Hard').title(); tour=str(getattr(m,'tour',None) or '')
        try:
            r=engine_obj.predict(a,b,surface,5 if str(getattr(m,'format','')).upper()=='BO5' else 3,simulations=12000)
            pick=a if r['p1_win']>=r['p2_win'] else b; prob=max(r['p1_win'],r['p2_win'])*100; ok+=1
            out.append(f'\n🎾 <b>{esc(a)} — {esc(b)}</b>\n{esc(tour)} • {surface}\n👉 {esc(pick)} <b>{prob:.1f}%</b>')
        except HistoricalPlayerMissingError as e:
            missing+=1
            log.warning('day match absent from historical state: %s / %s; missing=%s',a,b,e.players)
            names=', '.join(e.players)
            out.append(f'\n⚠️ {esc(a)} — {esc(b)}\nНет в исторической базе: {esc(names)}.')
        except Exception as e:
            failed+=1
            log.exception('day prediction failed for %s / %s',a,b)
            out.append(f'\n⚠️ {esc(a)} — {esc(b)}\nОшибка расчёта; подробность записана в журнал.')
    out.append(f'\nМатчей в API: {len(rows)} | рассчитано: {ok} | нет профиля: {missing} | ошибки: {failed}')
    return ('\n'.join(out), len(rows))

VIKA_BUSY_PHRASES = {
    'start_day': _dialog('working_day'),
    'start_live': _dialog('working_live'),
    'still_day': _dialog('still_working'),
    'still_live': _dialog('still_working'),
}

async def _run_with_progress(update, worker, start_text, still_text, interval=20):
    status = await update.message.reply_text(start_text)
    task = asyncio.create_task(asyncio.to_thread(worker))
    elapsed = 0
    try:
        while not task.done():
            await asyncio.sleep(interval)
            if task.done():
                break
            elapsed += interval
            mins, secs = divmod(elapsed, 60)
            tail = f' Уже {mins} мин {secs:02d} сек.' if mins else f' Уже {secs} сек.'
            try:
                await status.edit_text(still_text + tail)
            except Exception:
                pass
        return await task
    except asyncio.CancelledError:
        if not task.done():
            task.cancel()
        raise


async def day_cmd(update,context):
    text,count=await _run_with_progress(update, lambda: _build_day_report(provider, engine), VIKA_BUSY_PHRASES['start_day'], VIKA_BUSY_PHRASES['still_day'])
    try:
        await update.message.reply_text('✅ Готово. Вот что получилось:')
    except Exception:
        pass
    for i in range(0,len(text),3900):
        await update.message.reply_text(text[i:i+3900],parse_mode=ParseMode.HTML)

def _build_live_report(provider_obj, engine_obj):
    if not provider_obj.available:
        return '❌ Live Tennis API не настроен.'
    try: matches=provider_obj.live_matches()
    except Exception as e: return f'❌ Live API: {esc(e)}'
    if not matches: return '🟢 Сейчас live-матчей не найдено. Я продолжаю следить и напишу сама, когда появится подходящая ситуация.'
    lines=['🔴 <b>LIVE СЕЙЧАС</b>', 'Проверяю матчи не только на победителя, но и на доступные дополнительные рынки.']
    suitable=0
    for m in matches[:40]:
        a,b=obj_name(m,'p1') or 'P1',obj_name(m,'p2') or 'P2'; mid=obj_id(m); score=getattr(m,'score','')
        lines.append(f'\n🎾 <b>{esc(a)} — {esc(b)}</b>\nСчёт: <code>{esc(score)}</code> • ID <code>{esc(mid)}</code>')
        try:
            surface=str(getattr(m,'surface',None) or 'Hard').title(); pre=engine_obj.predict(a,b,surface,3,simulations=3000); pre['p1']=a; pre['p2']=b; pre['best_of']=3
            live=engine_obj.update_live(pre,frame_of(m)); cs=market_candidates(a,b,live,pre,frame_of(m))[:4]
            if cs:
                suitable += len(cs)
                for c in cs: lines.append(f'  • {esc(c["label"])} — модель {c["prob"]*100:.0f}% | fair {c["fair_odds"]:.2f}')
            else:
                lines.append('  • Пока подходящего рынка для входа не вижу.')
        except Exception as e:
            log.debug('live report %s/%s: %s',a,b,e)
            lines.append('  • Не хватило данных для расчёта этого матча.')
    if suitable == 0:
        lines.append('\n🟡 <b>Подходящей ставки сейчас не вижу.</b> Это нормально — AUTO-LIVE продолжит мониторить матчи в фоне.')
    else:
        lines.append(f'\n🟢 Подходящих кандидатов: <b>{suitable}</b>.')
    return '\n'.join(lines)

async def live_cmd(update,context):
    text=await _run_with_progress(update, lambda: _build_live_report(provider, engine), VIKA_BUSY_PHRASES['start_live'], VIKA_BUSY_PHRASES['still_live'], interval=15)
    await update.message.reply_text('✅ LIVE проверен. Вот что вижу сейчас:')
    await update.message.reply_text(text,parse_mode=ParseMode.HTML)

async def status_cmd(update,context):
    r=ModelHealth().report(); chat_id=getattr(update.effective_chat,'id',None)
    live_state = 'OK' if provider.available else 'OFF — нет ключа/клиента Live Tennis API'
    odds_state = 'OK' if odds_provider.available else 'OFF — мульти-рынки без внешней линии'
    auto_state = 'ВКЛ' if chat_id in AUTO_ENABLED else 'ВЫКЛ'
    q=provider.quota(refresh=True) if provider.available else {}
    rem=q.get('remaining')
    quota_text = f'{q.get("calls")} / {q.get("limit_per_day",100)} использовано, осталось {rem}' if rem is not None else 'не удалось получить usage'
    interval=provider.suggested_auto_interval() if provider.available else None
    interval_text=f'{interval//60} мин' if interval else 'пауза до сброса'
    msg=(f'🟢 <b>Vika status</b>\nCore: {"OK" if r["ok"] else "MISSING"}\n'
         f'Live model: <code>{esc(r.get("live_artifact") or "fallback")}</code>\n'
         f'Live API: <b>{esc(live_state)}</b>\n'
         f'API quota: <b>{esc(quota_text)}</b>\n'
         f'Следующий авто-скан: примерно <b>{esc(interval_text)}</b>\n'
         f'Odds API: <b>{esc(odds_state)}</b>\n'
         f'Автомониторинг этого чата: <b>{auto_state}</b>\n'
         f'Чатов в авто-LIVE: <b>{len(AUTO_ENABLED)}</b>\n'
         f'Чатов для дневной рассылки: <b>{len(CHATS)}</b>')
    await update.message.reply_text(msg,parse_mode=ParseMode.HTML)

async def form_cmd(update,context):
    if not context.args:return await update.message.reply_text('Напиши фамилию игрока.')
    name=' '.join(context.args);p=player(normalize_name(name)) or player(name)
    if not p:return await update.message.reply_text(f'❌ Игрок {name} пока не найден в state.')
    await update.message.reply_text(f'🎾 <b>{esc(p.name)}</b>\nПоследние 5: {p.form(5)*100:.1f}%\nПоследние 10: {p.form(10)*100:.1f}%\nМатчи 30д: {p.matches_30d}',parse_mode=ParseMode.HTML)

def _analyze_live_match(m):
    """Return (signal_or_none, diagnostic) for one live match."""
    a,b=obj_name(m,'p1'),obj_name(m,'p2'); mid=obj_id(m)
    diag={'match_id':mid,'p1':a,'p2':b,'reason':'no_signal','candidate_markets':0,'markets':[]}
    if not a or not b or not mid:
        diag['reason']='invalid_match'; return None,diag
    frame=frame_of(m); surface=str(frame.get('surface') or getattr(m,'surface',None) or 'Hard').title()
    try:
        pre=engine.predict(a,b,surface,3,simulations=6000); pre['p1']=a; pre['p2']=b; pre['best_of']=3
        live=engine.update_live(pre,frame)
    except Exception as e:
        diag['reason']='analysis_error'; diag['error']=str(e); return None,diag
    odds=extract_odds(frame)
    pre_p=max(float(pre.get('p1_win',.5)),float(pre.get('p2_win',.5)))
    live_p=max(float(live.get('p1_win',.5)),float(live.get('p2_win',.5)))
    pre_side=a if pre.get('p1_win',.5)>=pre.get('p2_win',.5) else b
    live_side=a if live.get('p1_win',.5)>=live.get('p2_win',.5) else b
    if pre_side!=live_side and pre_p>=.62 and live_p>=.62:
        diag['reason']='conflict'; return None,diag
    try:
        candidates=market_candidates(a,b,live,pre,frame)
    except Exception as e:
        diag['reason']='analysis_error'; diag['error']=str(e); return None,diag
    diag['candidate_markets']=len(candidates)
    diag['markets']=sorted({str(c.get('market','unknown')) for c in candidates})
    if not candidates:
        diag['reason']='no_market'; return None,diag
    chosen=None
    if odds_provider.available:
        try:
            quotes=odds_provider.markets(a,b)
            for c in candidates:
                for q in quotes:
                    if c['market']=='match_winner' and q['market']=='h2h':
                        if q['name'] not in (c['side'],a,b): continue
                    elif c['market']=='game_handicap' and q['market']=='spreads':
                        if q.get('name')!=c.get('side'): continue
                        if q.get('point') is not None and abs(float(q['point'])-float(c['line']))>1.01: continue
                    elif c['market']=='total_games' and q['market']=='totals':
                        if str(q.get('name','')).lower() not in ('over','under'): continue
                        if q.get('point') is not None and abs(float(q['point'])-float(c['line']))>1.01: continue
                        if ('over' in str(q.get('name','')).lower()) != (c.get('side')=='ТБ'): continue
                    else: continue
                    edge=c['prob']*float(q['price'])-1
                    if float(q['price'])>=c['fair_odds']*1.02 and edge>=.05:
                        chosen=(c,float(q['price']),edge,q); break
                if chosen: break
        except Exception as e:
            log.debug('odds provider: %s',e); diag['odds_error']=str(e)
    if not chosen and odds:
        for c in candidates:
            if c['market']!='match_winner': continue
            side_idx=0 if c['side']==a else 1; o=odds[side_idx]; edge=c['prob']*o-1
            if o>=c['fair_odds']*1.02 and edge>=.05:
                chosen=(c,o,edge,{'bookmaker':'Live Tennis API'}); break
    if not chosen:
        diag['reason']='no_price' if not odds_provider.available and not odds else 'no_value'
        return None,diag
    c,o,edge,q=chosen
    diag['reason']='signal'; diag['selected_market']=c.get('market'); diag['selected_label']=c.get('label'); diag['edge']=edge
    return {'a':a,'b':b,'mid':mid,'score':str(frame.get('score') or getattr(m,'score','')),'c':c,'o':o,'edge':edge,'q':q},diag

async def auto_live_cycle(app):
    started=datetime.now().timestamp()
    if not provider.available:
        return
    scan={'matches_found':0,'matches_analyzed':0,'candidate_markets':0,'signals':0,'api_errors':0,'reasons':{},'markets':{}}
    try:
        matches=provider.live_matches(auto=True)
        scan['matches_found']=len(matches or [])
        if not matches:
            scan['duration_sec']=round(datetime.now().timestamp()-started,1); auto_report.record_scan(scan); return
    except Exception as e:
        scan['api_errors']=1; scan['reasons']={'analysis_error':1}; scan['duration_sec']=round(datetime.now().timestamp()-started,1)
        auto_report.record_scan(scan); log.warning('live scan: %s',e); return
    for m in matches:
        try:
            result,diag=await asyncio.to_thread(_analyze_live_match,m)
            scan['matches_analyzed'] += 1
            scan['candidate_markets'] += int(diag.get('candidate_markets',0) or 0)
            for market in diag.get('markets') or []: scan['markets'][market]=scan['markets'].get(market,0)+1
            reason=diag.get('reason','no_signal'); scan['reasons'][reason]=scan['reasons'].get(reason,0)+1
            if not result: continue
            a,b,mid,score,c,o,edge,q=result['a'],result['b'],result['mid'],result['score'],result['c'],result['o'],result['edge'],result['q']
            key=f'{mid}:{c["market"]}:{c["side"]}:{c.get("line")}'
            now=datetime.now().timestamp(); last=LAST_SIGNALS.get(key,0)
            if now-last<1800: continue
            LAST_SIGNALS[key]=now; scan['signals'] += 1
            text=(f'🚨 <b>VIKA AUTO-LIVE СИГНАЛ</b>\n\n🎾 <b>{esc(a)} — {esc(b)}</b>\n📊 Счёт: <code>{esc(score)}</code>\n\n'
                  f'🎯 <b>{esc(c["label"])}</b>\n📚 Рынок: <b>{esc(c["market"])}</b>\n🔥 Модель: <b>{c["prob"]*100:.1f}%</b>\n💰 Коэффициент: <b>{o:.2f}</b> | fair: <b>{c["fair_odds"]:.2f}</b> | edge: <b>{edge*100:+.1f}%</b>\n🏦 Источник: {esc(q.get("bookmaker") if isinstance(q,dict) else "API")}\n'
                  f'🧠 Confidence: <b>{c["confidence"]*100:.0f}%</b>\n\n⚠️ Перед входом перепроверь, что рынок и коэффициент ещё актуальны.')
            for chat in list(AUTO_ENABLED):
                try: await app.bot.send_message(chat_id=chat,text=text,parse_mode=ParseMode.HTML)
                except Exception as e: log.warning('send signal %s: %s',chat,e)
        except Exception as e:
            scan['reasons']['analysis_error']=scan['reasons'].get('analysis_error',0)+1
            log.debug('auto match: %s',e)
    scan['duration_sec']=round(datetime.now().timestamp()-started,1)
    auto_report.record_scan(scan)
    log.info('AUTO-LIVE report: %s', scan)

async def auto_monitor(app):
    log.info('quota-safe auto-live monitor started')
    while True:
        if provider.available:
            await auto_live_cycle(app)
            interval = provider.suggested_auto_interval()
            if interval is None:
                log.warning('Auto-LIVE paused: daily free quota reserve reached; usage will resume after UTC reset.')
                await asyncio.sleep(900)
                continue
            log.info('next AUTO-LIVE scan in %ss', interval)
            await asyncio.sleep(int(os.getenv('LIVE_SCAN_SECONDS_OVERRIDE', interval)))
        else:
            await asyncio.sleep(120)


async def daily_scheduler(app):
    tz=ZoneInfo(os.getenv('VIKA_TIMEZONE','Europe/Moscow'));hour=int(os.getenv('DAILY_FORECAST_HOUR','9'));minute=int(os.getenv('DAILY_FORECAST_MINUTE','0'))
    while True:
        now=datetime.now(tz);stamp=now.strftime('%Y-%m-%d')
        if now.hour==hour and now.minute==minute and LAST_DAILY.get('date')!=stamp:
            LAST_DAILY['date']=stamp
            for chat in list(CHATS):
                try:
                    class Dummy: pass
                    # direct generation without fabricating Update
                    if not provider.available:continue
                    rows=provider.current_day();lines=['☀️ <b>VIKA — УТРЕННИЙ ОБЗОР</b>']
                    for m in rows[:30]:
                        a,b=obj_name(m,'p1'),obj_name(m,'p2')
                        if not a or not b:continue
                        try:
                            surface=str(getattr(m,'surface',None) or 'Hard').title();r=engine.predict(a,b,surface,3,simulations=12000);pick=a if r['p1_win']>=r['p2_win'] else b;prob=max(r['p1_win'],r['p2_win']);lines.append(f'\n🎾 {esc(a)} — {esc(b)}\n👉 {esc(pick)} <b>{prob*100:.1f}%</b>')
                        except Exception:pass
                    await app.bot.send_message(chat_id=chat,text='\n'.join(lines),parse_mode=ParseMode.HTML)
                except Exception as e:log.warning('daily: %s',e)
        await asyncio.sleep(30)

async def callbacks(update,context):
    q=update.callback_query;await q.answer();chat=q.message.chat_id
    if q.data=='day':
        CHATS.add(chat);await q.message.reply_text('Собираю расписание и прогоняю модель…');
        # minimal fake update isn't needed; call helper via a tiny proxy
        class U: pass
        u=U();u.message=q.message;u.effective_chat=q.message.chat
        await day_cmd(u,context)
    elif q.data=='live':
        class U: pass
        u=U();u.message=q.message;u.effective_chat=q.message.chat
        await live_cmd(u,context)
    elif q.data=='auto_on':AUTO_ENABLED.add(chat);CHATS.add(chat);await q.message.reply_text(_dialog('auto_on'),reply_markup=menu())
    elif q.data=='auto_off':AUTO_ENABLED.discard(chat);await q.message.reply_text(_dialog('auto_off'),reply_markup=menu())
    elif q.data=='status':
        class U: pass
        u=U();u.message=q.message;u.effective_chat=q.message.chat
        await status_cmd(u,context)

async def text_handler(update,context):
    text=(update.message.text or '').strip();low=text.lower();CHATS.add(update.effective_chat.id)
    if any(x in low for x in ('привет','здравств','что делать','помоги','меню','ку','приветик','добрый вечер','ты тут','тут?','ты здесь','ты здесь?','на месте','есть кто')):
        return await update.message.reply_text(_dialog('hello') + ' Я здесь 🙂 Могу посмотреть день, LIVE или сама включить мониторинг и прислать сигнал, когда увижу подходящий момент.',reply_markup=menu())
    if any(x in low for x in ('отчёт авто','отчет авто','лог авто','что ночью','ночной отчёт','ночной отчет','отчёт мониторинга','отчет мониторинга')):
        return await auto_report_cmd(update,context)
    if any(x in low for x in ('авто','автомат','сама следи','сам следи','мониторь','мониторинг')):
        AUTO_ENABLED.add(update.effective_chat.id);return await update.message.reply_text(_dialog('auto_on'))
    if any(x in low for x in ('стоп авто','выключи авто','не следи')):
        AUTO_ENABLED.discard(update.effective_chat.id);return await update.message.reply_text(_dialog('auto_off'))
    if any(x in low for x in ('сегодня','на день','на сегодня','расписание')) and not parse_match(text)[0]:return await day_cmd(update,context)
    if any(x in low for x in ('лайв','live','живые матчи','что там идёт')) and not parse_match(text)[0]:return await live_cmd(update,context)
    p1,p2,_=parse_match(text)
    if p1 and p2:return await predict_match_text(update,text)
    await update.message.reply_text(_dialog('unknown'),reply_markup=menu())

async def auto_report_cmd(update,context):
    await update.message.reply_text(auto_report.format_today(),parse_mode=ParseMode.HTML)

async def post_init(app):
    global MONITOR_TASK
    MONITOR_TASK=asyncio.create_task(auto_monitor(app));asyncio.create_task(daily_scheduler(app))
    log.info('Vika auto-live monitor started')

def main():
    token=os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:raise SystemExit('TELEGRAM_BOT_TOKEN is required in .env')
    app=Application.builder().token(token).post_init(post_init).build()
    commands=[('start',start),('help',help_cmd),('predict',predict_cmd),('day',day_cmd),('today',day_cmd),('upcoming',day_cmd),('form',form_cmd),('live',live_cmd),('status',status_cmd),('health',status_cmd),('auto_report',auto_report_cmd)]
    for c,f in commands:app.add_handler(CommandHandler(c,f))
    app.add_handler(CallbackQueryHandler(callbacks));app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler));app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=='__main__':main()
