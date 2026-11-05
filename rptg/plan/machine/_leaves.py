"""Финальные дети узла rptg.plan.machine в обёртках условий.

Сгенерировано tools/codegen0.py по design/rptg.plan.machine.yaml — не править руками.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rptg import _contract as _c
from . import intake as _m_intake
from . import policy as _m_policy
from . import element as _m_element
from . import settle as _m_settle
from . import refresh as _m_refresh
from . import close as _m_close

if TYPE_CHECKING:
    from rptg._types import Acceptance, Answer, Assignments, Config, Event, Evidences, Json, Override, Sha, Strings
    from rptg.plan._types import Absorbed, EventFacts, KindDecisions, Obs, Policies, PolicyStep, Settled
    from rptg.plan.machine._types import Acceptances, RecheckJobs, RecheckStored, RecheckTargets, Reports



class intake:
    """Лист rptg.plan.machine.intake: операции в обёртках условий."""

    @staticmethod
    def facts(state: Json, event: Event, evidence: Evidences, answer: Answer, cfg: Config) -> EventFacts:
        """предмет: у ответа модели — предмет задачи; у прогона — function:узел:операция или assembly:узел по цели; у ответа пользователя — design:X утверждения, предмет решения или перепроверки; у команды — карта корня. Роль — из задачи, иначе из назначения элемента, иначе по виду (карта и разложение корня — architect, разложение и сборка — designer, функция — implementer). Элемент — текущий или новый planned. Провалы и unknown — по вердикту. Разложение узла — чистый ответ разложения (без провалов и unknown), иначе текущее. ready — элемент ответа модели без назначения"""
        result = _m_intake.facts(state=state, event=event, evidence=evidence, answer=answer, cfg=cfg)
        _c.check('rptg.plan.machine.intake:facts', 'ensures', [
            ('len(result.ready) <= 1', lambda: (len(result.ready) <= 1)),
        ])
        return result

    @staticmethod
    def store(state: Json, facts: EventFacts, answer: Answer, evidence: Json, hash: Sha, cost: str, assignments: Assignments, cfg: Config) -> Json:
        """доказательства события дописываются к предмету; у ответа модели: не повтор по хэшу — attempts = max(attempts, попытка задачи) и хэш в answer_hashes; tokens и cost элемента и spent бюджета растут на расход; элементу без назначения — восстановленное: оператор задачи, ступень по лестнице роли, класс и источник кандидата (оператор не совпал — table); чистый ответ (извлечён, без провалов и unknown) пишется: карта — текст, карточка корня, типы; разложение — само, карточки детей, его типы; функция — код"""
        result = _m_intake.store(state=state, facts=facts, answer=answer, evidence=evidence, hash=hash, cost=cost, assignments=assignments, cfg=cfg)
        return result

    @staticmethod
    def observe(state: Json, facts: EventFacts, reports: Reports, acceptance: Acceptance, hash: Sha) -> Obs:
        """подтип — по первому провалу: P1 и не извлечённый или не разобранный код (Э1) — form; P2, P3, прочий Э1 — contract; P4 — dependency; P5, P7 — semantic; Э2, Э3, Э6 — value; иначе other; провалов нет — none. same — подпись отчётов (слой, правило, место) против отчётов элемента до события: провалов или прежних отчётов нет — NA. Текущий хэш — у последнего доказательства предмета; complete — на нём есть провал или unknown, либо все слои: у функции Э1 от mypy, Э2 и Э3, у сборки Э6, у карты и разложения — любое. unknown — провалов нет, а есть unknown или всё на месте без приёмки (недоверенная проверка). repeat — хэш ответа уже был у элемента"""
        result = _m_intake.observe(state=state, facts=facts, reports=reports, acceptance=acceptance, hash=hash)
        return result

    @staticmethod
    def idle(state: Json, subject: str, assignments: Assignments) -> Obs:
        """наблюдаемые самого элемента без нового события — чтобы найти вызов в позиции: подтип — последний подтип элемента (нет — none), same — NA, попытки и tokens элемента, класс — назначения элемента, иначе первого из списка, иначе map; complete — да, accepted, unknown, repeat — нет"""
        result = _m_intake.idle(state=state, subject=subject, assignments=assignments)
        return result


class policy:
    """Лист rptg.plan.machine.policy: операции в обёртках условий."""

    @staticmethod
    def build(cfg: Config) -> Policies:
        """у роли своя политика cfg.policies[роль] — её корень, иначе дерево по умолчанию: SEQ ступеней по длине лестницы роли и STOP(exhausted). Ступень 1 — CALL assigned [primary], CHECK, SWITCH violation_subtype {none → STOP(accepted), form → повторы формы, contract и semantic → починки} default CHECK. Ступень k > 1 — CALL next [primary + отчёт], CHECK, SWITCH violation_subtype {form → повторы формы} default CHECK, SWITCH same_failure {SAME → STOP(card_suspect)} default CHECK, SWITCH violation_subtype {none → STOP(accepted), contract и semantic → починки} default CHECK. Повторы формы (repair.form_retries штук) — SEQ[CALL same [alternative], CHECK, SWITCH violation_subtype {none → STOP(accepted), form → следующий повтор} default CHECK]; починки (repair.per_rung штук) — SEQ[CALL same [primary + отчёт], CHECK, SWITCH violation_subtype {none → STOP(accepted), form → повторы формы, contract и semantic → следующая починка} default CHECK]. Дерево extra — SEQ[CALL same [primary + отчёт], CHECK, SWITCH violation_subtype {none → STOP(accepted)} default STOP(user)]. problems пуст"""
        result = _m_policy.build(cfg=cfg)
        _c.check('rptg.plan.machine.policy:build', 'ensures', [
            ('len(result.problems) == 0', lambda: (len(result.problems) == 0)),
        ])
        return result

    @staticmethod
    def check(policies: Policies, cfg: Config) -> Policies:
        """у каждого дерева (architect, designer, implementer, extra) обходом сверху вниз, путь в записи arch2; проблема — «роль: путь: что»: неизвестный узел; CALL — оператор не assigned, same, next и не оператор проекта, формулировка не primary и не alternative, за CALL в его SEQ нет CHECK; SEQ и PAR — пустой список детей, у SEQ узлы после STOP; SWITCH — неизвестная наблюдаемая, значение не из наблюдаемой, нет default, tokens_bucket вне BUDGET; BUDGET — лимит не положителен или нет child; STOP без причины. Итог — те же деревья и найденные проблемы"""
        result = _m_policy.check(policies=policies, cfg=cfg)
        return result

    @staticmethod
    def step(policies: Policies, state: Json, subject: str, obs: Obs, idle: Obs, manual: Override, event: str, assignments: Assignments, cfg: Config) -> PolicyStep:
        """ответ пользователя и команда — none; сборка — без дерева: проверка не полна — check, принята — stop accepted, провал — stop blame; элемент ждёт пользователя — none. Дерево — extra при режиме extra, иначе роли. Вызов в позиции: хранимый путь на CALL — он, иначе исполнение от начала режима (reopen, resume, пусто — root) по наблюдаемым idle до первого CALL. dispatch — этот вызов; ответ модели — повтор оставляет его, unknown — stop unknown, иначе исполнение от следующего за ним узла; прогон — от хранимой позиции (CHECK) по наблюдаемым события. Исполнение: CHECK не полон — ждать; SEQ и PAR — первый ребёнок; SWITCH — ветвь значения или default; рамка BUDGET — расход наблюдаемых (позиция ищется по расходу до события, дальше — после): вход в исчерпанную рамку и приход к CALL под ней — stop budget, рамка ограничивает следующие вызовы, а не полученный ответ; STOP — stop с причиной; ветвь кончилась — следующий узел родителя, у PAR после провала ветви — следующая ветвь; конец дерева — accepted по приёмке, иначе exhausted. Приход к CALL: assigned — назначение элемента, same — текущий оператор, next — ступень + 1, если она не выше min(лестница, max_rung), иначе stop exhausted; имя оператора — он. Отчёт — with_report или первый вызов режима reopen"""
        result = _m_policy.step(policies=policies, state=state, subject=subject, obs=obs, idle=idle, manual=manual, event=event, assignments=assignments, cfg=cfg)
        _c.check('rptg.plan.machine.policy:step', 'ensures', [
            ('result.wait == "call" => result.rung >= 1', lambda: ((not (result.wait == "call")) or (result.rung >= 1))),
        ])
        return result


class element:
    """Лист rptg.plan.machine.element: операции в обёртках условий."""

    @staticmethod
    def update(state: Json, facts: EventFacts, obs: Obs, step: PolicyStep, reports: Json, manual: Override, design_hash: Sha) -> Absorbed:
        """шаг none — элемент как есть. Провал — отчёты и подтип провала; приёмка — отчётов нет, подтип none. Вызов: повтор — позиция и состояние прежние, запись repeat; иначе позиция шага, назначение — оператор и ступень шага, состояние: alternative — form_retry и form_retries + 1, ступень выше — escalated, иначе с отчётом — repairing, иначе planned. check — checking. stop: accepted — approval у разложения корня и узла с ручным approve, иначе accepted; unknown — checking и ожидание пользователя; exhausted, card_suspect, blame — card_suspect (следствия решает settle); прочая причина — card_suspect и ожидание пользователя. route — узел принятого разложения"""
        result = _m_element.update(state=state, facts=facts, obs=obs, step=step, reports=reports, manual=manual, design_hash=design_hash)
        return result

    @staticmethod
    def reply(absorbed: Absorbed, cfg: Config) -> Absorbed:
        """прочие события — как есть. Утверждение {approve, design_hash, decision}: элемент не на утверждении или дайджест не тот — запись stale_reply; yes — разложение принято, утверждение записано (версию записала ревизия по ответу модели), route — узел; no — разложение и карточки его детей сняты, элементы поддерева тоже (они принадлежали отвергнутой версии, следующая разведёт детей заново), отчёт с комментарием: у корня карта переоткрывается с ним, разложение корня — заново; у поддерева переоткрывается разложение"""
        result = _m_element.reply(absorbed=absorbed, cfg=cfg)
        return result

    @staticmethod
    def decide(absorbed: Absorbed, cfg: Config) -> Absorbed:
        """прочие события — как есть. Решение {decide, decision} по элементу, что ждёт пользователя: retry — элемент переоткрывается; revise — владелец (разложение родителя, у узла корня — корень) переоткрывается с отчётами элемента и комментарием, элемент ждёт владельца с прежней позицией. Перепроверка {recheck}: unknown на текущем хэше сняты, элемент stale с прежней позицией. Команда budget — новый лимит; на каждую команду — запись command"""
        result = _m_element.decide(absorbed=absorbed, cfg=cfg)
        return result


class settle:
    """Лист rptg.plan.machine.settle: операции в обёртках условий."""

    @staticmethod
    def children(absorbed: Absorbed, kinds: KindDecisions, cfg: Config) -> Settled:
        """карта принята — разложение корня planned (архитектор), если его нет. Разложение узла X принято (route) — дети по видам: составной — design:C, финальный — function:C:операция для каждой операции (есть код — stale, перепроверка без модели, иначе planned), и assembly:X; записи route. changed пуст"""
        result = _m_settle.children(absorbed=absorbed, kinds=kinds, cfg=cfg)
        return result

    @staticmethod
    def revision(before: Json, settled: Settled, absorbed: Absorbed) -> Settled:
        """ответ модели на разложение узла Y прошёл проверки (шаг — stop accepted; у разложения на утверждении — тоже: его принимает пользователь, а прежней версии к тому времени в состоянии нет). Версия — хэш разложения: та же, что последняя, — как есть; совпала с позапрошлой — колебание: запись oscillation, элемент ждёт пользователя; дописывается. Была прежняя версия — ревизия: карточки детей, что изменились, — в changed; снятые дети — их поддерево из состояния; подозреваемые под Y, чья карточка не менялась (владелец оставил карточку), продолжают: round + 1, позиция — resume к ветви default подозрения, на исчерпанной лестнице — extra. Прочие события — как есть"""
        result = _m_settle.revision(before=before, settled=settled, absorbed=absorbed)
        return result

    @staticmethod
    def suspect(settled: Settled, absorbed: Absorbed, cfg: Config) -> Settled:
        """stop exhausted у функции ниже max_depth — повышение: функции узла promoted, design:узел planned, запись promotion. stop card_suspect или exhausted (разложение, max_depth), E3 с малом годных входов — подозрение на карточку узла: корень — ожидание пользователя; round ≥ 1 — повтор состояния, ожидание пользователя; иначе владелец — разложение родителя — переоткрывается с отчётами элемента"""
        result = _m_settle.suspect(settled=settled, absorbed=absorbed, cfg=cfg)
        return result

    @staticmethod
    def blame(settled: Settled, absorbed: Absorbed, cfg: Config) -> Settled:
        """stop blame у сборки: виновный — из подробностей первого провала Э6, по умолчанию разложение узла; design:X или function:узел:операция переоткрывается с отчётами сборки (запись blame); card:X — карточка X под подозрением: переоткрывается её владелец — разложение родителя X, у корня — разложение корня; иначе — как есть"""
        result = _m_settle.blame(settled=settled, absorbed=absorbed, cfg=cfg)
        return result


class refresh:
    """Лист rptg.plan.machine.refresh: операции в обёртках условий."""

    @staticmethod
    def remove(settled: Settled, dead: Strings, cfg: Config) -> Settled:
        """фаза DESIGN, все разложения приняты, ни одного на утверждении и под подозрением, мёртвые есть — каскадом: операции из карточек, их схемы из разложений; узел без операций — вместе с поддеревом и ребёнком в разложении родителя; элементы снятого. Узлы с изменившимися карточками — в changed; запись revision со списком; изменилось разложение корня — оно снова на утверждении. Иначе — как есть"""
        result = _m_refresh.remove(settled=settled, dead=dead, cfg=cfg)
        return result

    @staticmethod
    def types(before: Json, settled: Settled) -> Settled:
        """типы, на которые ссылались до снятия и не ссылаются после, снимаются; ссылки — типы параметров и результатов операций карточек и записи схем разложений, замыканием по $ref схем типов; ничего не снято — как есть"""
        result = _m_refresh.types(before=before, settled=settled)
        return result

    @staticmethod
    def restart(settled: Settled) -> Settled:
        """разложения и функции узлов из changed без сохранённой версии (разложения, кода) начинаются заново на новой карточке: planned, без назначения, позиции, отчётов и хэшей ответов — прежние провалы и повторы относились к старой карточке, перепроверять нечего; повышенные функции остаются как есть"""
        result = _m_refresh.restart(settled=settled)
        return result

    @staticmethod
    def targets(settled: Settled, stale: Strings) -> RecheckTargets:
        """предметы перепроверки — устаревшие по check.stale и элементы в stale, без повторов, по порядку; снятые и ждущие утверждения пропускаются (их только что проверили, приёмку даёт пользователь); сборка — planned (прогон позже); карта с текстом, разложение с сохранённой версией и функция с кодом — в предметы, их элементы — stale; значение — карта (текст, карточка и типы корня), разложение без поля node, у функции — пустой объект; каноническую запись даст lang"""
        result = _m_refresh.targets(settled=settled, stale=stale)
        _c.check('rptg.plan.machine.refresh:targets', 'ensures', [
            ('len(result.values) == len(result.subjects)', lambda: (len(result.values) == len(result.subjects))),
        ])
        return result

    @staticmethod
    def jobs(targets: RecheckTargets, texts: Strings, cfg: Config) -> RecheckJobs:
        """событие ответа модели на предмет: задача — предмет, вид по предмету (map, design, function), роль и оператор назначения элемента (нет — первый лестницы роли), попытка элемента (не меньше 1), primary; ответ — у карты и разложения их каноническая запись, у функции код в блоке python; расход нулевой, finish_reason recheck"""
        _c.check('rptg.plan.machine.refresh:jobs', 'requires', [
            ('len(texts) == len(targets.subjects)', lambda: (len(texts) == len(targets.subjects))),
        ])
        result = _m_refresh.jobs(targets=targets, texts=texts, cfg=cfg)
        _c.check('rptg.plan.machine.refresh:jobs', 'ensures', [
            ('len(result.events) == len(result.subjects)', lambda: (len(result.events) == len(result.subjects))),
        ])
        return result

    @staticmethod
    def store(jobs: RecheckJobs, results: Json) -> RecheckStored:
        """доказательства каждого события — к его предмету; провалы по порядку"""
        result = _m_refresh.store(jobs=jobs, results=results)
        return result

    @staticmethod
    def apply(settled: Settled, stored: RecheckStored, acceptances: Acceptances, reports: Json, cfg: Config) -> Settled:
        """по предмету: принят — accepted; провал — переоткрыт с его отчётами, round 0; функция без провала статики — checking в режиме recheck (прогоны позже); unknown — ожидание пользователя; записи recheck"""
        _c.check('rptg.plan.machine.refresh:apply', 'requires', [
            ('len(acceptances) == len(stored.subjects)', lambda: (len(acceptances) == len(stored.subjects))),
        ])
        result = _m_refresh.apply(settled=settled, stored=stored, acceptances=acceptances, reports=reports, cfg=cfg)
        return result


class close:
    """Лист rptg.plan.machine.close: операции в обёртках условий."""

    @staticmethod
    def phase(before: Json, absorbed: Absorbed, settled: Settled, cfg: Config) -> Json:
        """фаза вперёд по состояниям (LOGIC §7.1): NEW → MAP с первым событием карты; разложение корня на утверждении — MAP_REVIEW; «нет» утверждения корня — MAP; «да» и дальше — DESIGN, пока есть непринятые разложения; BUILD — все разложения приняты; E2E — приняты функции и сборки кроме корня; DONE — принята сборка корня. PAUSED — команда pause или элемент ждёт пользователя из-за колебания, повтора состояния или бюджета задачи; из PAUSED выводит resume или ответ пользователя. DONE не меняется"""
        result = _m_close.phase(before=before, absorbed=absorbed, settled=settled, cfg=cfg)
        return result

    @staticmethod
    def journal(before: Json, after: Json, absorbed: Absorbed, settled: Settled, evidence: Json) -> Json:
        """итог: состояние после, доказательства события как есть; журнал — по записи evidence на доказательство события, записи впитывания и следствий, по записи state на каждый изменившийся элемент (предмет, было, стало) по порядку предметов, запись phase при смене фазы, запись budget при смене расхода, запись outcome на каждый элемент, пришедший в accepted, promoted или card_suspect"""
        result = _m_close.journal(before=before, after=after, absorbed=absorbed, settled=settled, evidence=evidence)
        return result
