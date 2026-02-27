import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useStore } from "../store/useStore";

function useCountUp(target, duration = 2000) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const started = useRef(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        const start = performance.now();
        const tick = (now) => {
          const p = Math.min((now - start) / duration, 1);
          const ease = 1 - Math.pow(1 - p, 3);
          setCount(Math.floor(ease * target));
          if (p < 1) requestAnimationFrame(tick);
          else setCount(target);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [target, duration]);
  return [count, ref];
}

function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAuthenticated } = useStore();
  const navigate = useNavigate();
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);
  const navLinks = [
    { label: "기능", href: "#features" },
    { label: "작동 방식", href: "#how" },
    { label: "전략", href: "#strategy" },
  ];
  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "bg-gray-900/95 backdrop-blur-md shadow-lg border-b border-gray-700/50" : "bg-transparent"}`}>
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <polyline points="16 7 22 7 22 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-bold text-white text-lg tracking-tight">Upbit<span className="text-blue-400">Auto</span></span>
        </div>
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((l) => (
            <a key={l.label} href={l.href} className="text-gray-300 hover:text-white text-sm font-medium transition-colors">{l.label}</a>
          ))}
        </nav>
        <div className="hidden md:flex items-center gap-3">
          {isAuthenticated ? (
            <button onClick={() => navigate("/dashboard")} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all">대시보드로 이동 →</button>
          ) : (
            <>
              <Link to="/login" className="text-gray-300 hover:text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-white/10 transition-all">로그인</Link>
              <Link to="/register" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all">무료 시작</Link>
            </>
          )}
        </div>
        <button className="md:hidden text-gray-300 hover:text-white p-2" onClick={() => setMobileOpen(!mobileOpen)}>
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            {mobileOpen ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/> : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16"/>}
          </svg>
        </button>
      </div>
      {mobileOpen && (
        <div className="md:hidden bg-gray-900/98 border-t border-gray-700/50 px-6 py-4 flex flex-col gap-4">
          {navLinks.map((l) => (<a key={l.label} href={l.href} className="text-gray-300 text-sm font-medium" onClick={() => setMobileOpen(false)}>{l.label}</a>))}
          <div className="flex flex-col gap-2 pt-2 border-t border-gray-700/50">
            <Link to="/login" className="text-center text-gray-300 text-sm py-2 border border-gray-600 rounded-lg">로그인</Link>
            <Link to="/register" className="text-center bg-blue-600 text-white text-sm py-2 rounded-lg">무료 시작</Link>
          </div>
        </div>
      )}
    </header>
  );
}

function HeroSection() {
  const [winRate, winRef] = useCountUp(87);
  const [users, usersRef] = useCountUp(2400);
  const [profit, profRef] = useCountUp(340);
  const [trades, trdRef] = useCountUp(18500);
  const stats = [
    { label: "평균 승률", value: winRate, suffix: "%", ref: winRef },
    { label: "누적 사용자", value: users, suffix: "명+", ref: usersRef },
    { label: "평균 수익률", value: profit, suffix: "%", ref: profRef },
    { label: "총 거래 건수", value: trades, suffix: "+", ref: trdRef },
  ];
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-gray-950 pt-16">
      <div className="absolute inset-0 opacity-20" style={{backgroundImage:"linear-gradient(to right,#1e3a5f 1px,transparent 1px),linear-gradient(to bottom,#1e3a5f 1px,transparent 1px)",backgroundSize:"60px 60px"}} />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-600/15 rounded-full blur-3xl" />
      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/30 rounded-full px-4 py-1.5 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-blue-300 text-sm font-medium">AI 기반 실시간 자동매매 시스템 가동 중</span>
        </div>
        <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-6">
          스마트한 <span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">암호화폐</span><br />자동매매의 시작
        </h1>
        <p className="text-gray-400 text-xl md:text-2xl mb-10 max-w-2xl mx-auto leading-relaxed">
          RSI·MACD·볼린저밴드 전략을 결합한 AI가<br className="hidden md:block" />24시간 최적의 매매 타이밍을 포착합니다.
        </p>
        <div className="flex flex-wrap justify-center gap-4 mb-20">
          <Link to="/register" className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all hover:scale-105 hover:shadow-xl hover:shadow-blue-500/30">지금 무료로 시작하기 →</Link>
          <Link to="/login" className="bg-white/10 hover:bg-white/20 border border-white/20 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all hover:scale-105 backdrop-blur-sm">로그인</Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} ref={s.ref} className="bg-white/5 border border-white/10 rounded-2xl p-5 backdrop-blur-sm hover:bg-white/10 transition-all">
              <div className="text-3xl font-black text-white mb-1">{s.value.toLocaleString()}{s.suffix}</div>
              <div className="text-gray-400 text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/></svg>
      </div>
    </section>
  );
}

function StatsBar() {
  const items = [
    { icon: "🏆", label: "3년+ 운영 경험", sub: "안정적인 서비스" },
    { icon: "⚡", label: "99.9% 가동률", sub: "24/7 무중단 운영" },
    { icon: "🛡️", label: "실시간 모니터링", sub: "이상 감지 자동 중단" },
    { icon: "📊", label: "다중 전략 지원", sub: "RSI · MACD · BB" },
  ];
  return (
    <section className="bg-gray-900 border-y border-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-3">
            <span className="text-2xl">{it.icon}</span>
            <div>
              <div className="text-white font-semibold text-sm">{it.label}</div>
              <div className="text-gray-500 text-xs">{it.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    { icon: "🤖", title: "AI 자동 매매", desc: "머신러닝 기반 알고리즘이 시장 데이터를 분석하여 최적의 매매 타이밍을 자동으로 결정합니다.", color: "from-blue-500/20 to-blue-600/5" },
    { icon: "📈", title: "실시간 차트 분석", desc: "다중 기술적 지표를 동시에 분석하여 정확도 높은 진입·청산 시그널을 생성합니다.", color: "from-green-500/20 to-green-600/5" },
    { icon: "🛡️", title: "리스크 관리", desc: "손절 라인, 포지션 크기, 일일 최대 손실 한도를 자동으로 관리하여 자산을 보호합니다.", color: "from-purple-500/20 to-purple-600/5" },
    { icon: "🔔", title: "알림 시스템", desc: "매매 실행, 수익 달성, 이상 상황 발생 시 즉시 알림을 받아 언제나 현황을 파악합니다.", color: "from-yellow-500/20 to-yellow-600/5" },
    { icon: "📊", title: "성과 분석", desc: "누적 수익률, 승률, 최대 낙폭 등 상세한 퍼포먼스 지표로 전략을 지속적으로 최적화합니다.", color: "from-indigo-500/20 to-indigo-600/5" },
    { icon: "⚡", title: "고속 주문 처리", desc: "업비트 API와 직접 연결되어 밀리초 단위의 빠른 주문 처리로 슬리피지를 최소화합니다.", color: "from-red-500/20 to-red-600/5" },
  ];
  return (
    <section id="features" className="bg-gray-950 py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">핵심 기능</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">수익을 위한 모든 도구</h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">전문 트레이더의 노하우를 AI 알고리즘으로 구현했습니다</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title} className="group relative bg-gray-900 border border-gray-800 rounded-2xl p-6 overflow-hidden hover:border-gray-600 transition-all hover:-translate-y-1">
              <div className={`absolute inset-0 bg-gradient-to-br ${f.color} opacity-0 group-hover:opacity-100 transition-opacity`} />
              <div className="relative z-10">
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="text-white font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorksSection() {
  const steps = [
    { num: "01", title: "회원가입", desc: "이메일로 간편하게 가입하고 업비트 API 키를 연결합니다." },
    { num: "02", title: "전략 설정", desc: "RSI, MACD, 볼린저밴드 중 원하는 전략과 파라미터를 선택합니다." },
    { num: "03", title: "봇 실행", desc: "한 번의 클릭으로 자동매매 봇이 24시간 시장을 모니터링합니다." },
    { num: "04", title: "수익 확인", desc: "실시간 대시보드에서 거래 내역과 수익 현황을 확인합니다." },
  ];
  return (
    <section id="how" className="bg-gray-900 py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">작동 방식</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">4단계로 시작하는 자동매매</h2>
          <p className="text-gray-400 text-lg">복잡한 설정 없이 누구나 쉽게 시작할 수 있습니다</p>
        </div>
        <div className="relative">
          <div className="hidden md:block absolute top-10 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-blue-500/50 to-transparent mx-24" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {steps.map((s) => (
              <div key={s.num} className="relative flex flex-col items-center text-center">
                <div className="relative z-10 w-20 h-20 rounded-full bg-gray-950 border-2 border-blue-500/50 flex items-center justify-center mb-6">
                  <span className="text-blue-400 font-black text-xl">{s.num}</span>
                </div>
                <h3 className="text-white font-bold text-lg mb-2">{s.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function TradingStrategySection() {
  const strategies = [
    { name: "RSI 전략", badge: "인기", badgeColor: "bg-green-500/20 text-green-400", desc: "과매수/과매도 구간을 정밀 포착하여 역추세 매매로 안정적 수익을 추구합니다.", stats: [{label:"평균 승률",val:73},{label:"월 수익률",val:18},{label:"리스크",val:32}] },
    { name: "MACD 전략", badge: "추천", badgeColor: "bg-blue-500/20 text-blue-400", desc: "이동평균 수렴·발산 지표로 추세 전환점을 조기에 포착합니다.", stats: [{label:"평균 승률",val:68},{label:"월 수익률",val:24},{label:"리스크",val:45}] },
    { name: "볼린저밴드", badge: "안정형", badgeColor: "bg-purple-500/20 text-purple-400", desc: "변동성 밴드를 활용해 가격 이탈 시 진입하는 평균회귀 전략입니다.", stats: [{label:"평균 승률",val:71},{label:"월 수익률",val:15},{label:"리스크",val:28}] },
  ];
  return (
    <section id="strategy" className="bg-gray-950 py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">트레이딩 전략</div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">검증된 매매 알고리즘</h2>
          <p className="text-gray-400 text-lg">백테스트와 실거래 데이터로 검증된 3가지 핵심 전략</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {strategies.map((s) => (
            <div key={s.name} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 hover:border-gray-600 transition-all hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-bold text-lg">{s.name}</h3>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${s.badgeColor}`}>{s.badge}</span>
              </div>
              <p className="text-gray-400 text-sm mb-5 leading-relaxed">{s.desc}</p>
              <div className="space-y-3">
                {s.stats.map((st) => (
                  <div key={st.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">{st.label}</span>
                      <span className="text-white font-semibold">{st.val}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full" style={{width:`${st.val}%`}} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTABanner() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 py-20">
      <div className="absolute inset-0 opacity-10" style={{backgroundImage:"radial-gradient(circle, #fff 1px, transparent 1px)",backgroundSize:"24px 24px"}} />
      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <h2 className="text-4xl md:text-5xl font-black text-white mb-4">지금 바로 시작하세요</h2>
        <p className="text-blue-100 text-xl mb-10">회원가입 후 즉시 자동매매를 시작할 수 있습니다.<br />복잡한 설정 없이 5분이면 충분합니다.</p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/register" className="bg-white text-blue-700 hover:bg-blue-50 px-8 py-4 rounded-xl text-lg font-bold transition-all hover:scale-105 shadow-xl">무료로 시작하기 →</Link>
          <Link to="/login" className="border-2 border-white/40 text-white hover:bg-white/10 px-8 py-4 rounded-xl text-lg font-semibold transition-all">로그인</Link>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="bg-gray-950 border-t border-gray-800 py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center">
                <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </div>
              <span className="font-bold text-white">UpbitAuto</span>
            </div>
            <p className="text-gray-500 text-sm leading-relaxed">AI 기반 업비트 자동매매 플랫폼.<br />스마트한 투자의 시작.</p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">서비스</h4>
            <ul className="space-y-2 text-gray-500 text-sm">
              <li><Link to="/register" className="hover:text-gray-300 transition-colors">회원가입</Link></li>
              <li><Link to="/login" className="hover:text-gray-300 transition-colors">로그인</Link></li>
              <li><a href="#features" className="hover:text-gray-300 transition-colors">기능 소개</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">안내</h4>
            <p className="text-gray-500 text-sm leading-relaxed">본 시스템은 투자 참고용이며,<br />투자 손실에 대한 책임은 사용자에게 있습니다.<br />암호화폐 투자 시 신중하게 결정하세요.</p>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-6 text-center text-gray-600 text-xs">© 2026 UpbitAuto. All rights reserved. | 업비트 자동매매 시스템 v3.0</div>
      </div>
    </footer>
  );
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-950">
      <SiteHeader />
      <HeroSection />
      <StatsBar />
      <FeaturesSection />
      <HowItWorksSection />
      <TradingStrategySection />
      <CTABanner />
      <SiteFooter />
    </div>
  );
}
