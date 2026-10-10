import { ArrowRight, ArrowUpRight, ChevronDown, ChevronLeft, ChevronRight, Menu, Play, Sparkles, X, Trophy, Clock, CheckCircle2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "wouter";
import { fetchCompetitionStatus } from "@/lib/supabase";

const GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScE4OXgmGns_catCz_TLUGF7SGN5ZOxMErQW4f08dEPdXV82Q/viewform?usp=dialog";

const partners = [
  { short: "RCM", name: "Rotary Club\nof Madras", logo: "/media/logo/rotary club of madras.png", mark: "✦" },
  { short: "VEP", name: "Rotaract Club\nof Vepery", logo: "/media/logo/rotaract club of vepery.png", mark: "◈" },
  { short: "VMR", name: "Rotaract Club\nof VMRF", logo: "/media/logo/rotaract club of vmrf.jpg", mark: "✺" },
  { short: "JEC", name: "Jeppiaar Engineering\nCollege", logo: "/media/logo/rotaract cub of jeppiaar enginnering college.png", mark: "◇" },
  { short: "JPU", name: "Jeppiaar\nUniversity", logo: "/media/logo/rotaract club of jeppiaar universirty.jpg", mark: "◒" },
  { short: "SDN", name: "SDNB Vaishnav\nCollege", logo: "/media/logo/rotaract club of sdnb vaishnac college.jpg", mark: "S" },
  { short: "TNC", name: "The New\nCollege", logo: "/media/logo/rotaract club of new college.png", mark: "N" },
  { short: "CHN", name: "Rotaract Club\nof Chennai", logo: "/media/logo/rotaract club of chennai.jpg", mark: "C" },
];

const faqs = [
  { q: "Who can participate?", a: "Participants aged 18 years and above from any educational background, college, institution or youth group are eligible." },
  { q: "What is the team size?", a: "Each team must consist of 2 to 5 members. A participant can be part of only one team." },
  { q: "What is the official theme?", a: "Mobile Phone Addiction, with a clear focus on mental health awareness, digital detachment, and human connection." },
  { q: "How long should the reel be?", a: "Reels must be between 25 and 45 seconds in duration. Entries outside this window cannot be accepted." },
  { q: "What format should the reel be?", a: "Vertical 9:16 portrait orientation. Recommended resolution is 1080 × 1920 pixels in MP4 or MOV format (maximum 100MB)." },
  { q: "What language can we use?", a: "Tamil, English, Hindi, Telugu, Malayalam or any other language. Subtitles in English are recommended for non-English entries." },
  { q: "Can AI tools be used?", a: "Yes. AI tools may be used for editing, animation, sound design, or voiceover, but the creative concept and script must reflect your team's originality." },
  { q: "Can we use copyrighted music?", a: "Teams are responsible for obtaining required permissions or using royalty-free music and sound effects." },
  { q: "When is the registration deadline?", a: "Official team registration closes on 7 October 2026 (IST)." },
  { q: "When is the reel submission deadline?", a: "Final video submissions close on 8 November 2026 at 23:59:59 IST." },
  { q: "What are the prizes?", a: "Total prize pool is ₹55,000 (1st Prize: ₹25,000 + Trophy, 2nd Prize: ₹15,000, 3rd Prize: ₹10,000, 4th Prize: ₹5,000)." },
  { q: "Will participants receive certificates?", a: "Yes, official Participation Certificates from Rotary Club of Madras and Rotaract Club of Vepery will be provided to all eligible entries." }
];

function Reveal({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        node.style.setProperty("--reveal-delay", `${delay}ms`);
        node.classList.add("is-visible");
        observer.disconnect();
      }
    }, { threshold: 0.12 });
    observer.observe(node);
    return () => observer.disconnect();
  }, [delay]);
  return <div ref={ref} className={`reveal ${className}`}>{children}</div>;
}

function SiteHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="neon-header">
      <Link href="/" className="neon-brand" aria-label="Mindscape home">
        <span className="neon-brand-word font-oblisk">Mind<span>scape</span></span>
        <small>REEL MAKING CONTEST</small>
      </Link>
      <nav className={open ? "neon-nav is-open" : "neon-nav"} aria-label="Main navigation">
        <a className="active" href="#home" onClick={() => setOpen(false)}>Home</a>
        <a href="#about" onClick={() => setOpen(false)}>About</a>
        <a href="#prizes" onClick={() => setOpen(false)}>Prizes</a>
        <Link href="/submit" onClick={() => setOpen(false)}>Submit Reel</Link>
        <a href="#faq" onClick={() => setOpen(false)}>FAQ</a>
        <Link href="/admin" onClick={() => setOpen(false)} style={{ color: "#ffd5ff", opacity: 0.8 }}>Admin</Link>
      </nav>
      <button className="neon-menu" onClick={() => setOpen(!open)} aria-label={open ? "Close menu" : "Open menu"}>
        {open ? <X size={22} /> : <Menu size={22} />}
      </button>
    </header>
  );
}

function Confetti() {
  return (
    <div className="confetti-field" aria-hidden="true">
      {Array.from({ length: 18 }).map((_, i) => (
        <i key={i} className={`confetti c-${i + 1}`} />
      ))}
    </div>
  );
}

function CountdownTimer() {
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [isSubmission, setIsSubmission] = useState(false);

  useEffect(() => {
    let timer: any;
    const calculateTime = () => {
      const now = new Date().getTime();
      const regDeadline = new Date("2026-10-07T23:59:59+05:30").getTime();
      const subDeadline = new Date("2026-11-08T23:59:59+05:30").getTime();

      if (now < regDeadline) {
        setIsSubmission(false);
        setSecondsLeft(Math.max(0, Math.floor((regDeadline - now) / 1000)));
      } else {
        setIsSubmission(true);
        setSecondsLeft(Math.max(0, Math.floor((subDeadline - now) / 1000)));
      }
    };

    calculateTime();
    timer = setInterval(calculateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const days = Math.floor(secondsLeft / 86400);
  const hours = Math.floor((secondsLeft % 86400) / 3600);
  const minutes = Math.floor((secondsLeft % 3600) / 60);
  const seconds = secondsLeft % 60;

  return (
    <div className="countdown-box">
      <div className="countdown-title">
        <Clock size={13} style={{ display: "inline-block", marginRight: 6, verticalAlign: "-2px" }} />
        {isSubmission ? "Reel Submissions Close In" : "Registration Closes In"}
      </div>
      <div className="countdown-grid">
        <div className="timer-unit">
          <div className="timer-number">{String(days).padStart(2, "0")}</div>
          <div className="timer-label">Days</div>
        </div>
        <div className="timer-separator">:</div>
        <div className="timer-unit">
          <div className="timer-number">{String(hours).padStart(2, "0")}</div>
          <div className="timer-label">Hours</div>
        </div>
        <div className="timer-separator">:</div>
        <div className="timer-unit">
          <div className="timer-number">{String(minutes).padStart(2, "0")}</div>
          <div className="timer-label">Mins</div>
        </div>
        <div className="timer-separator">:</div>
        <div className="timer-unit">
          <div className="timer-number">{String(seconds).padStart(2, "0")}</div>
          <div className="timer-label">Secs</div>
        </div>
      </div>
    </div>
  );
}

function HeroReel() {
  return (
    <div className="neon-hero-art" aria-label="3D reel making contest illustration">
      <div className="hero-halo halo-a" />
      <div className="hero-halo halo-b" />
      <div className="hero-orbit orbit-a" />
      <div className="hero-orbit orbit-b" />
      <div className="clapper clapper-top">
        <span /><span /><span /><span /><span />
      </div>
      <div className="clapper clapper-body">
        <div className="clapper-lens" />
        <div className="clapper-screen">
          <Play fill="currentColor" size={47} />
          <span>YOUR STORY</span>
        </div>
        <div className="clapper-controls"><i /><i /><i /><b /></div>
      </div>
      <div className="floating-film film-one" />
      <div className="floating-film film-two" />
      <div className="hero-arrow">➜</div>
    </div>
  );
}

function PhoneStack() {
  return (
    <div className="phone-scene" aria-label="3D reel cards preview">
      <div className="phone-ring ring-one" />
      <div className="phone-ring ring-two" />
      <div className="phone-card phone-back">
        <span>01</span>
        <strong>behind<br />the<br /><em>screen.</em></strong>
      </div>
      <div className="phone-card phone-mid">
        <span>REEL / 02</span>
        <strong>look up<br />from the<br /><em>feed.</em></strong>
      </div>
      <div className="phone-card phone-front">
        <div className="phone-top">
          <span>◉</span>
          <span className="font-oblisk">mindscape</span>
          <b>⋯</b>
        </div>
        <div className="phone-image">
          <div className="phone-sun" />
          <div className="phone-person" />
        </div>
        <div className="phone-bottom">
          <strong>change<br /><em>a mind</em></strong>
          <span>▶ 00:35</span>
        </div>
      </div>
      <div className="phone-note note-one">Real Stories.<br /><em>Bigger Impact.</em></div>
      <div className="phone-note note-two">✦ 25 — 45 sec</div>
    </div>
  );
}

export default function Home() {
  const [clubIndex, setClubIndex] = useState(0);
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const activePartners = partners.slice(clubIndex, clubIndex + 6);
  if (activePartners.length < 6) {
    activePartners.push(...partners.slice(0, 6 - activePartners.length));
  }

  const moveHero = (event: React.MouseEvent<HTMLElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setMouse({
      x: ((event.clientX - rect.left) / rect.width - 0.5) * 2,
      y: ((event.clientY - rect.top) / rect.height - 0.5) * 2,
    });
  };

  return (
    <div className="neon-site" onMouseMove={moveHero} style={{ "--mouse-x": mouse.x, "--mouse-y": mouse.y } as React.CSSProperties}>
      <SiteHeader />
      <main>
        {/* ===================== HERO SECTION ===================== */}
        <section className="neon-hero" id="home">
          <div className="neon-bg-cloud cloud-one" />
          <div className="neon-bg-cloud cloud-two" />
          <div className="neon-bg-cloud cloud-three" />
          <div className="neon-stars" />
          <Confetti />
          <div className="neon-hero-inner">
            <Reveal className="neon-hero-copy">
              <p className="neon-kicker">
                ROTARY CLUB OF MADRAS & ROTARACT CLUB OF VEPERY<br />
                <span>PRESENT</span>
              </p>
              <h1 className="font-oblisk">Mind<span>scape</span></h1>
              <p className="neon-subtitle">REEL MAKING CONTEST ON MOBILE PHONE ADDICTION</p>
              <p className="neon-hero-description">
                <strong>What if a reel could change a mind?</strong><br />
                25–45 seconds. One idea. One message. Turn short-form creativity into meaningful digital awareness and mental health impact.
              </p>
              <div className="neon-hero-actions">
                <a className="neon-button neon-button-primary" href={GOOGLE_FORM_URL} target="_blank" rel="noreferrer">
                  Register Your Team <ArrowRight size={19} />
                </a>
                <Link className="neon-text-button" href="/submit">
                  Upload Reel Directly <ArrowUpRight size={16} />
                </Link>
              </div>
              <div className="neon-open-state">
                <span className="live-pulse" /> ₹55,000 Prize Pool · Submissions Open · Chennai '26
              </div>

              {/* Countdown Component */}
              <CountdownTimer />
            </Reveal>

            <Reveal className="neon-hero-visual" delay={120}>
              <HeroReel />
            </Reveal>
          </div>
          <div className="hero-scroll-cue">
            <span>scroll to discover</span>
            <span className="cue-line" />
          </div>
        </section>

        {/* ===================== ABOUT SECTION ===================== */}
        <section className="neon-about" id="about">
          <div className="neon-grid-lines" />
          <div className="neon-section-inner">
            <Reveal className="neon-about-copy">
              <p className="neon-section-label">ABOUT THE INITIATIVE</p>
              <h2>Behind Every Screen<br /><span>is a Human Story</span></h2>
              <p className="neon-body-copy">
                Mindscape is a Mental Health Awareness Initiative centered around Mobile Phone Addiction, inviting young creators and students across Chennai and beyond to use short-form vertical visual storytelling to encourage digital detachment and healthier habits.
              </p>
              <p className="neon-body-copy" style={{ marginTop: 14 }}>
                Explore through: <strong>Acting • Storytelling • Humour • Animation • Memes • Visual Poetry</strong>.
              </p>
              <div className="neon-rule">
                <i /><i /><i />
              </div>
            </Reveal>

            <Reveal className="neon-about-art" delay={120}>
              <PhoneStack />
            </Reveal>
          </div>
        </section>

        {/* ===================== PARTNERS / COLLABORATION ===================== */}
        <section className="neon-partners" id="partners">
          <Reveal className="neon-centered-heading">
            <p className="neon-section-label">IN COLLABORATION WITH</p>
            <h2>Host & Supporting <span>Institutions</span></h2>
          </Reveal>
          <div className="partner-carousel">
            <button
              className="circle-arrow"
              onClick={() => setClubIndex((index) => (index - 1 + partners.length) % partners.length)}
              aria-label="Previous partner"
            >
              <ChevronLeft size={20} />
            </button>
            <div className="partner-orbit-line" />
            {activePartners.map((partner, index) => (
              <Reveal
                key={`${partner.short}-${clubIndex}-${index}`}
                className={`partner-orb ${index === 2 ? "selected" : ""}`}
                delay={index * 55}
              >
                <div className="partner-orb-inner">
                  {partner.logo ? (
                    <img
                      src={partner.logo}
                      alt={partner.name}
                      className="partner-logo-img"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                        if (e.currentTarget.parentElement) {
                          e.currentTarget.parentElement.innerHTML = `<span>${partner.mark}</span><small>${partner.short}</small>`;
                        }
                      }}
                    />
                  ) : (
                    <>
                      <span>{partner.mark}</span>
                      <small>{partner.short}</small>
                    </>
                  )}
                </div>
                <p>
                  {partner.name.split("\n").map((line) => (
                    <span key={line}>{line}</span>
                  ))}
                </p>
              </Reveal>
            ))}
            <button
              className="circle-arrow"
              onClick={() => setClubIndex((index) => (index + 1) % partners.length)}
              aria-label="Next partner"
            >
              <ChevronRight size={20} />
            </button>
          </div>
          <div className="carousel-dots">
            {partners.slice(0, 5).map((_, i) => (
              <i className={i === clubIndex % 5 ? "active" : ""} key={i} />
            ))}
          </div>
        </section>

        {/* ===================== PRIZES SECTION ===================== */}
        <section className="neon-about" id="prizes" style={{ background: "radial-gradient(ellipse at 50% 30%, rgba(139, 48, 255, 0.25), transparent 45%), #08041d" }}>
          <div className="neon-grid-lines" />
          <div style={{ maxWidth: 1240, margin: "auto", padding: "90px clamp(22px, 8.8vw, 140px)" }}>
            <Reveal className="neon-centered-heading">
              <p className="neon-section-label">GRAND AWARDS</p>
              <h2>₹55,000 <span>Prize Pool</span></h2>
              <p style={{ color: "#c7bcdb", maxWidth: 540, margin: "14px auto 0", fontSize: 16 }}>
                Rewarding transformative visual storytelling addressing mobile phone addiction with cash awards, trophies, and official recognition.
              </p>
            </Reveal>

            <div className="prize-poster-grid">
              <Reveal className="award-poster-tile tile-spotlight-1st" delay={50}>
                <div className="tile-number">01</div>
                <div className="tile-rank-title">1ST PRIZE</div>
                <div className="tile-headline">The One That Changed The Mind</div>
                <div className="tile-prize-amount">₹25,000</div>
                <div className="tile-award-details">
                  Cash Award + Grand Trophy + Winner Certificate for all team members
                </div>
              </Reveal>

              <Reveal className="award-poster-tile" delay={100}>
                <div className="tile-number">02</div>
                <div className="tile-rank-title">2ND PRIZE</div>
                <div className="tile-headline">Runner-Up Excellence</div>
                <div className="tile-prize-amount">₹15,000</div>
                <div className="tile-award-details">
                  Cash Award + Runner-Up Trophy + Certificate of Merit
                </div>
              </Reveal>

              <Reveal className="award-poster-tile" delay={150}>
                <div className="tile-number">03</div>
                <div className="tile-rank-title">3RD PRIZE</div>
                <div className="tile-headline">Creative Visionary</div>
                <div className="tile-prize-amount">₹10,000</div>
                <div className="tile-award-details">
                  Cash Award + Recognition Trophy + Certificate of Merit
                </div>
              </Reveal>

              <Reveal className="award-poster-tile" delay={200}>
                <div className="tile-number">04</div>
                <div className="tile-rank-title">4TH PRIZE</div>
                <div className="tile-headline">Special Jury Mention</div>
                <div className="tile-prize-amount">₹5,000</div>
                <div className="tile-award-details">
                  Cash Award + Certificate of Excellence
                </div>
              </Reveal>
            </div>

            <div style={{ textAlign: "center", marginTop: 36 }}>
              <span className="meta-badge badge-valid" style={{ fontSize: 12, padding: "8px 20px" }}>
                <CheckCircle2 size={14} style={{ display: "inline", marginRight: 6 }} />
                Participation certificates will be provided to all eligible participating teams.
              </span>
            </div>
          </div>
        </section>

        {/* ===================== CALL TO ACTION ===================== */}
        <section className="neon-cta" id="register">
          <div className="cta-glow glow-left" />
          <div className="cta-glow glow-right" />
          <Confetti />
          <div className="cta-reel-fragment fragment-left" />
          <div className="cta-reel-fragment fragment-right" />
          <Reveal className="neon-cta-content">
            <p className="neon-section-label">CREATE SOMETHING THAT SPEAKS</p>
            <h2>The Next Big <span>Reel</span></h2>
            <p>
              Your reel could be 45 seconds.<br />
              Its impact on someone looking at their phone could last much longer.
            </p>
            <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap", marginTop: 24 }}>
              <a className="neon-button neon-button-primary" href={GOOGLE_FORM_URL} target="_blank" rel="noreferrer">
                Register Team ↗ <ArrowRight size={19} />
              </a>
              <Link className="neon-button neon-button-outline" href="/submit" style={{ borderColor: "#fff", color: "#fff" }}>
                Upload Reel Studio <ArrowUpRight size={17} />
              </Link>
            </div>
          </Reveal>
        </section>

        {/* ===================== FAQ ACCORDION ===================== */}
        <section className="neon-faq" id="faq">
          <Reveal className="neon-centered-heading">
            <p className="neon-section-label">COMMON QUESTIONS</p>
            <h2>Frequently Asked <span>Questions</span></h2>
            <p className="faq-copy">Everything you need to know about participating in MINDSCAPE 2026.</p>
          </Reveal>

          <div className="neon-accordion">
            {faqs.map((faq, i) => (
              <div key={i} className={`neon-accordion-item ${openFaq === i ? "open" : ""}`}>
                <button
                  className="neon-accordion-question"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  aria-expanded={openFaq === i}
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    size={18}
                    style={{
                      transform: openFaq === i ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.25s ease",
                    }}
                  />
                </button>
                {openFaq === i && (
                  <div className="neon-accordion-answer">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 45 }}>
            <Link href="/submit" className="neon-button neon-button-outline">
              Ready? Submit your reel <ArrowUpRight size={17} />
            </Link>
          </div>
        </section>
      </main>

      {/* ===================== FOOTER ===================== */}
      <footer className="neon-footer">
        <div className="footer-brand-lockup">
          <span className="neon-brand-word font-oblisk">Mind<span>scape</span></span>
          <small>REEL MAKING CONTEST</small>
        </div>
        <p>
          A Mental Health Awareness Initiative by <strong>Rotary Club of Madras</strong><br />
          Hosted by <strong>Rotaract Club of Vepery</strong> and supporting college clubs across Chennai.
        </p>
        <div className="footer-bottom-neon">
          <span>© 2026 Mindscape · Mobile Phone Addiction Reel Contest</span>
          <span>
            made with <Sparkles size={13} /> in Chennai
          </span>
        </div>
      </footer>
    </div>
  );
}
