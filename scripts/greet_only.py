#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_JOB = "ai应用研发工程师"
DEFAULT_TARGET = 150
DEFAULT_MAX_SCANS = 150
REQUIRED_MESSAGE_HEADINGS = (
    "真人化说明",
    "一条合并岗位介绍",
    "索要附件简历",
)


class CampaignError(RuntimeError):
    pass


class GreetingKnowledgeBaseError(CampaignError):
    pass


@dataclass(frozen=True)
class Candidate:
    geek_id: str
    name: str
    base_info: str
    expect: str
    experience: str
    advantage: str
    highlights: Tuple[str, ...]
    can_greet: bool
    has_history_chat: bool
    has_viewed: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Candidate":
        highlights = value.get("highlights")
        if not isinstance(highlights, list):
            highlights = []
        return cls(
            geek_id=str(value.get("geekId") or "").strip(),
            name=str(value.get("name") or "").strip(),
            base_info=str(value.get("baseInfo") or "").strip(),
            expect=str(value.get("expect") or "").strip(),
            experience=str(value.get("experience") or "").strip(),
            advantage=str(value.get("advantage") or "").strip(),
            highlights=tuple(str(item).strip() for item in highlights if str(item).strip()),
            can_greet=bool(value.get("canGreet")),
            has_history_chat=bool(value.get("hasHistoryChat")),
            has_viewed=bool(value.get("hasViewed")),
        )

    def searchable_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.base_info,
                self.expect,
                self.experience,
                self.advantage,
                *self.highlights,
            )
            if part
        )


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    school: str = ""
    major: str = ""
    degree: str = ""
    grad_year: Optional[int] = None


@dataclass(frozen=True)
class CampaignResult:
    initial_count: int
    final_count: int
    scanned: int
    refreshed: int


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _extract_inline_code_after_heading(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$"
        rf"(?P<body>.*?)(?=^###\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if not match:
        raise GreetingKnowledgeBaseError(f"知识库缺少“{heading}”段落")
    snippets = re.findall(r"`([^`\r\n]+)`", match.group("body"))
    if len(snippets) != 1:
        raise GreetingKnowledgeBaseError(
            f"知识库“{heading}”必须且只能包含一条行内代码话术，当前为 {len(snippets)} 条"
        )
    message = snippets[0].strip()
    if not message:
        raise GreetingKnowledgeBaseError(f"知识库“{heading}”话术为空")
    return message


def load_greeting_messages(path: Path) -> Tuple[str, str, str]:
    try:
        markdown = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GreetingKnowledgeBaseError(f"无法读取知识库：{path}: {exc}") from exc
    messages = tuple(
        _extract_inline_code_after_heading(markdown, heading)
        for heading in REQUIRED_MESSAGE_HEADINGS
    )
    if len(messages) != 3:
        raise GreetingKnowledgeBaseError("知识库必须提供三条主动招呼消息")
    return messages  # type: ignore[return-value]


def _parse_target_schools(path: Path) -> Tuple[Tuple[str, ...], Dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    schools: List[str] = []
    aliases: Dict[str, str] = {}
    in_school_list = False
    in_alias_table = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## 目标学校"):
            in_school_list = True
            in_alias_table = False
            continue
        if line.startswith("## 学校别名"):
            in_school_list = False
            in_alias_table = True
            continue
        if line.startswith("## ") and not line.startswith("## 学校别名"):
            if schools:
                in_school_list = False
            if in_alias_table:
                in_alias_table = False
        if in_school_list:
            match = re.match(r"^\d+\.\s+(.+?)\s*$", line)
            if match:
                schools.append(match.group(1))
        elif in_alias_table and line.startswith("|") and "---" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 2 or cells[0] in {"标准名称", ""}:
                continue
            official, raw_aliases = cells
            for alias in re.split(r"[,，]", raw_aliases):
                alias = alias.strip()
                if alias and alias != official:
                    aliases[alias] = official
    if not schools:
        raise CampaignError(f"未从目标学校知识库读取到学校：{path}")
    return tuple(schools), aliases


def _parse_allowed_majors(path: Path) -> Tuple[str, ...]:
    text = path.read_text(encoding="utf-8")
    majors: List[str] = []
    in_majors = False
    for raw_line in text.splitlines():
        if re.match(r"^\s*allowed_majors:\s*$", raw_line):
            in_majors = True
            continue
        if not in_majors:
            continue
        match = re.match(r'^\s+-\s+"([^"]+)"\s*$', raw_line)
        if match:
            majors.append(match.group(1))
            continue
        if raw_line.strip() and not raw_line.startswith((" ", "\t")):
            break
        if re.match(r"^\s{2}\w", raw_line) and not raw_line.lstrip().startswith("-"):
            break
    if not majors:
        raise CampaignError(f"未从专业知识库读取到允许专业：{path}")
    return tuple(majors)


@dataclass(frozen=True)
class EligibilityPolicy:
    schools: Tuple[str, ...]
    aliases: Mapping[str, str]
    majors: Tuple[str, ...]

    @classmethod
    def from_files(cls, target_schools: Path, school_policy: Path) -> "EligibilityPolicy":
        schools, aliases = _parse_target_schools(target_schools)
        return cls(
            schools=schools,
            aliases=aliases,
            majors=_parse_allowed_majors(school_policy),
        )

    def _find_school(self, text: str) -> str:
        matches: List[Tuple[int, str]] = []
        normalized = _normalize(text)
        for school in self.schools:
            if _normalize(school) in normalized:
                matches.append((len(_normalize(school)), school))
        for alias, official in self.aliases.items():
            if _normalize(alias) in normalized:
                matches.append((len(_normalize(alias)), official))
        if not matches:
            return ""
        matches.sort(reverse=True)
        return matches[0][1]

    def _find_major(self, text: str) -> str:
        normalized = _normalize(text)
        matches = [
            major for major in self.majors if _normalize(major) in normalized
        ]
        if not matches:
            return ""
        return max(matches, key=lambda item: len(_normalize(item)))

    @staticmethod
    def _degree_level(degree: str) -> int:
        return {
            "本科": 1,
            "研究生": 2,
            "硕士": 2,
            "博士": 3,
        }.get(degree, 0)

    def _final_education_text(self, candidate: Candidate, degree: str) -> str:
        education_text = " ".join(
            part
            for part in (
                candidate.experience,
                candidate.advantage,
                *candidate.highlights,
            )
            if part
        )
        record_pattern = re.compile(r"(博士研究生|硕士研究生|博士|硕士|研究生|本科)")
        matches = list(record_pattern.finditer(education_text))
        if matches:
            requested_level = self._degree_level(degree)
            records: List[Tuple[str, str]] = []
            for index, match in enumerate(matches):
                end = (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(education_text)
                )
                record_degree = match.group(1)
                if record_degree.startswith("博士"):
                    record_degree = "博士"
                elif record_degree.startswith("硕士"):
                    record_degree = "硕士"
                records.append((record_degree, education_text[match.start():end]))
            same_level = [
                text
                for record_degree, text in records
                if self._degree_level(record_degree) == requested_level
            ]
            if same_level:
                return same_level[-1]
            return ""
        return candidate.searchable_text()

    def evaluate(self, candidate: Candidate) -> EligibilityResult:
        base = candidate.base_info
        if not re.search(r"(?:27年应届生|2027(?:年|届)?)", base):
            return EligibilityResult(False, "graduation_year")
        degree_match = re.search(r"(博士|硕士|研究生|本科)", base)
        if not degree_match:
            return EligibilityResult(False, "degree")
        education_text = self._final_education_text(
            candidate, degree_match.group(1)
        )
        school = self._find_school(education_text)
        if not school:
            return EligibilityResult(False, "school_unknown_or_ineligible")
        major = self._find_major(education_text)
        if not major:
            return EligibilityResult(False, "major_unknown_or_ineligible")
        return EligibilityResult(
            True,
            "eligible",
            school=school,
            major=major,
            degree=degree_match.group(1),
            grad_year=2027,
        )


class BossCli:
    def __init__(self, executable: str = "boss", timeout_seconds: int = 90):
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def _run(self, arguments: Sequence[str]) -> str:
        try:
            result = subprocess.run(
                [self.executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise CampaignError(f"找不到 boss 命令：{self.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CampaignError(
                f"boss 命令超时：{' '.join(arguments[:2])}"
            ) from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise CampaignError(
                f"boss {' '.join(arguments[:2])} 失败：{detail or 'unknown error'}"
            )
        return result.stdout.strip()

    def recommend(self, job: str, refresh: bool) -> List[Candidate]:
        args = ["recommend", job, "--json"]
        if refresh:
            args.append("--refresh")
        raw = self._run(args)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CampaignError("boss recommend --json 返回了无效 JSON") from exc
        if payload.get("job") != job and job not in str(payload.get("job") or ""):
            raise CampaignError(
                f"推荐岗位不匹配：期望“{job}”，实际“{payload.get('job') or 'unknown'}”"
            )
        values = payload.get("candidates")
        if not isinstance(values, list):
            raise CampaignError("boss recommend --json 缺少 candidates 数组")
        candidates = [
            Candidate.from_mapping(item)
            for item in values
            if isinstance(item, dict)
        ]
        return [
            candidate
            for candidate in candidates
            if candidate.geek_id and candidate.name
        ]

    def greet(self, candidate: Candidate, job: str) -> None:
        raw = self._run(
            [
                "greet",
                candidate.name,
                "--id",
                candidate.geek_id,
                "--job",
                job,
                "--json",
            ]
        )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CampaignError("boss greet --json 返回了无效 JSON") from exc
        actual_job = str(payload.get("job") or "")
        if job not in actual_job:
            raise CampaignError(
                f"打招呼岗位不匹配：期望“{job}”，实际“{actual_job or 'unknown'}”"
            )
        if payload.get("geekId") != candidate.geek_id:
            raise CampaignError("打招呼结果候选人 ID 不匹配")
        if payload.get("name") != candidate.name:
            raise CampaignError("打招呼结果候选人姓名不匹配")

    def open_exact_chat(self, candidate: Candidate, job: str) -> str:
        output = self._run(["chat", candidate.name, "--strict"])
        required = (
            f"成功进入候选人聊天：{candidate.name}",
            f"姓名: {candidate.name}",
            f"沟通职位: {job}",
        )
        missing = [item for item in required if item not in output]
        if missing:
            raise CampaignError(
                f"精确会话验证失败，缺少：{' / '.join(missing)}"
            )
        return output

    def send(self, message: str) -> None:
        output = self._run(["send", "--text", message])
        if f"已发送消息：{message}" not in output:
            raise CampaignError("消息发送结果无法验证")


class RuntimeStoreCli:
    def __init__(self, script: Path):
        self.script = script

    def _run_json(self, arguments: Sequence[str]) -> Mapping[str, object]:
        try:
            result = subprocess.run(
                [sys.executable, str(self.script), *arguments],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise CampaignError("运行状态命令超时") from exc
        if result.returncode != 0:
            raise CampaignError(
                f"运行状态命令失败：{(result.stderr or result.stdout).strip()}"
            )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CampaignError("运行状态命令返回了无效 JSON") from exc
        if not isinstance(value, dict):
            raise CampaignError("运行状态命令未返回 JSON 对象")
        return value

    def greeting_count(self, date: str) -> int:
        return int(self._run_json(["greeting-count", "--date", date])["count"])

    def is_deduped(self, candidate_id: str, at: str) -> bool:
        return bool(
            self._run_json(
                ["dedupe-check", "--candidate-id", candidate_id, "--at", at]
            )["deduped"]
        )

    def record_greeted(
        self,
        candidate: Candidate,
        eligibility: EligibilityResult,
        job: str,
        at: str,
    ) -> None:
        self._run_json(
            [
                "greeting-complete",
                "--candidate-id",
                candidate.geek_id,
                "--display-name",
                candidate.name,
                "--greeted-at",
                at,
                "--job",
                job,
                "--school",
                eligibility.school,
                "--major",
                eligibility.major,
                "--degree",
                eligibility.degree,
                "--grad-year",
                str(eligibility.grad_year or 2027),
            ]
        )

    def mark_waiting_resume(
        self,
        candidate: Candidate,
        eligibility: EligibilityResult,
        at: str,
    ) -> None:
        self._run_json(
            [
                "candidate-upsert",
                "--candidate-id",
                candidate.geek_id,
                "--display-name",
                candidate.name,
                "--stage",
                "waiting_resume",
                "--now",
                at,
                "--school",
                eligibility.school,
                "--major",
                eligibility.major,
                "--degree",
                eligibility.degree,
                "--grad-year",
                "2027",
                "--last-contact-at",
                at,
            ]
        )


class CampaignRunner:
    def __init__(
        self,
        *,
        boss,
        store,
        policy: EligibilityPolicy,
        messages: Tuple[str, str, str],
        job: str,
        target: int,
        max_scans: int,
        now: Callable[[], datetime],
    ):
        if target < 1 or target > 150:
            raise CampaignError("目标招呼数必须在 1 到 150 之间")
        if max_scans < 1 or max_scans > 150:
            raise CampaignError("检查候选人上限必须在 1 到 150 之间")
        if len(messages) != 3:
            raise GreetingKnowledgeBaseError("必须从知识库读取到三条消息")
        self.boss = boss
        self.store = store
        self.policy = policy
        self.messages = messages
        self.job = job
        self.target = target
        self.max_scans = max_scans
        self.now = now

    def _now(self) -> datetime:
        value = self.now()
        if value.tzinfo is None:
            raise CampaignError("当前时间必须包含时区")
        return value.astimezone(SHANGHAI)

    def _assert_send_window(self) -> datetime:
        current = self._now()
        if current.hour < 9 or current.hour >= 21:
            raise CampaignError("当前不在 Asia/Shanghai 09:00–21:00 招聘时段")
        return current

    def _send_messages(self, candidate: Candidate) -> None:
        for message in self.messages:
            self._assert_send_window()
            self.boss.open_exact_chat(candidate, self.job)
            self.boss.send(message)
            conversation = self.boss.open_exact_chat(candidate, self.job)
            if message not in conversation:
                raise CampaignError(
                    f"候选人 {candidate.name} 的消息发送后无法在会话中验证"
                )

    def run(self) -> CampaignResult:
        current = self._assert_send_window()
        date = current.date().isoformat()
        initial_count = self.store.greeting_count(date)
        if initial_count >= self.target:
            return CampaignResult(initial_count, initial_count, 0, 0)

        seen_ids = set()
        scanned = 0
        refresh_next = False
        refreshed = 0
        consecutive_empty_batches = 0
        max_empty_batches = max(1, (self.max_scans + 9) // 10)

        while True:
            current_count = self.store.greeting_count(date)
            if current_count >= self.target:
                return CampaignResult(
                    initial_count=initial_count,
                    final_count=current_count,
                    scanned=scanned,
                    refreshed=refreshed,
                )
            if scanned >= self.max_scans:
                raise CampaignError(
                    f"已达到本次检查候选人上限 {self.max_scans}，"
                    f"当前招呼数 {current_count}/{self.target}"
                )

            candidates = self.boss.recommend(self.job, refresh_next)
            if refresh_next:
                refreshed += 1
            refresh_next = False
            name_counts = Counter(
                item.name for item in candidates if item.geek_id and item.name
            )

            distinct = []
            for item in candidates:
                if item.geek_id in seen_ids:
                    continue
                distinct.append(item)
                if len(distinct) == 10:
                    break

            if not distinct:
                consecutive_empty_batches += 1
                if consecutive_empty_batches >= max_empty_batches:
                    raise CampaignError(
                        f"连续刷新 {consecutive_empty_batches} 次仍没有新的候选人，"
                        f"当前招呼数 {current_count}/{self.target}"
                    )
                refresh_next = True
                continue
            consecutive_empty_batches = 0

            selected: Optional[Tuple[Candidate, EligibilityResult]] = None
            for item in distinct:
                if scanned >= self.max_scans:
                    break
                seen_ids.add(item.geek_id)
                scanned += 1
                if not item.can_greet:
                    continue
                if name_counts[item.name] > 1:
                    continue
                eligibility = self.policy.evaluate(item)
                if not eligibility.eligible:
                    continue
                at = self._now().isoformat()
                if self.store.is_deduped(item.geek_id, at):
                    continue
                selected = (item, eligibility)
                break

            if selected is None:
                refresh_next = True
                continue

            eligible_candidate, eligibility = selected
            action_time = self._assert_send_window().isoformat()
            self.boss.greet(eligible_candidate, self.job)
            self.store.record_greeted(
                eligible_candidate,
                eligibility,
                self.job,
                action_time,
            )
            self._send_messages(eligible_candidate)
            self.store.mark_waiting_resume(
                eligible_candidate,
                eligibility,
                self._now().isoformat(),
            )
            print(
                json.dumps(
                    {
                        "event": "greeted",
                        "count": self.store.greeting_count(date),
                        "target": self.target,
                        "scanned": scanned,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )


class CampaignLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd: Optional[int] = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(
                str(self.path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError as exc:
            raise CampaignError(
                f"已有打招呼执行器锁：{self.path}。确认没有其他执行器后再删除该锁。"
            ) from exc
        os.write(self.fd, str(os.getpid()).encode("ascii"))
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _state_root() -> Path:
    configured = os.environ.get("BOSS_ZHAOPIN_STATE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex" / "state" / "boss-zhaopin"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="仅执行 Boss 主动打招呼和知识库三条消息"
    )
    parser.add_argument("--job", default=DEFAULT_JOB)
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--max-scans", type=int, default=DEFAULT_MAX_SCANS)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="确认执行真实 Boss 打招呼与消息发送；未提供时只做配置校验",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.target < 1 or args.target > 150:
        print("停止：目标招呼数必须在 1 到 150 之间", file=sys.stderr)
        return 2
    if args.max_scans < 1 or args.max_scans > 150:
        print("停止：检查候选人上限必须在 1 到 150 之间", file=sys.stderr)
        return 2
    root = _repository_root()
    skill_root = root / "skills" / "boss-zhaopin"
    messages = load_greeting_messages(skill_root / "references" / "greetings.md")
    policy = EligibilityPolicy.from_files(
        skill_root / "references" / "target_schools.md",
        skill_root / "references" / "school_policy.yaml",
    )
    if not args.execute:
        print(
            json.dumps(
                {
                    "validated": True,
                    "job": args.job,
                    "target": args.target,
                    "maxScans": args.max_scans,
                    "messageCount": len(messages),
                },
                ensure_ascii=False,
            )
        )
        return 0

    store = RuntimeStoreCli(skill_root / "scripts" / "runtime_store.py")
    runner = CampaignRunner(
        boss=BossCli(),
        store=store,
        policy=policy,
        messages=messages,
        job=args.job,
        target=args.target,
        max_scans=args.max_scans,
        now=lambda: datetime.now(SHANGHAI),
    )
    lock_path = _state_root() / "greet-only.lock"
    try:
        with CampaignLock(lock_path):
            result = runner.run()
    except KeyboardInterrupt:
        print("停止：收到 Ctrl+C，已安全释放执行器锁", file=sys.stderr)
        return 130
    except CampaignError as exc:
        print(f"停止：{exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "initialCount": result.initial_count,
                "finalCount": result.final_count,
                "scanned": result.scanned,
                "refreshed": result.refreshed,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
