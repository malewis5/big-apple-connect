// Facts about the site shared by metadata, structured data, robots.txt and
// the sitemap. bigappleconnect.com redirects to the www host, so www is canonical.
export const SITE_URL = "https://www.bigappleconnect.com";
export const SITE_NAME = "Big Apple Connect Box";
export const SITE_TITLE = "Big Apple Connect Box: Is your NYCHA internet as good as promised?";
export const SITE_DESCRIPTION =
  "A free, open-source box that measures home internet speed and reliability day and night, so NYCHA residents can check New York City's Big Apple Connect promise and keep the proof.";
export const REPO = "https://github.com/malewis5/big-apple-connect-box";

// The page's words, shared by the HTML page and its Markdown version (/index.md).
export const hero = {
  eyebrow: "For homes in New York City public housing",
  title: "Is your internet as good as promised?",
  body: "New York City promises NYCHA residents free, fast and reliable internet. We're building a small box that checks that promise from inside the home, day and night.",
};

export const storySteps = [
  {
    title: "It starts with a tiny computer.",
    body: "A Raspberry Pi is a whole computer the size of a credit card. It costs about $35.",
  },
  {
    title: "We give it a simple home.",
    body: "A plain white case keeps it safe. It's small enough to sit right next to your router.",
  },
  {
    title: "Plug it into your router.",
    body: "One cable connects the box to your router. Plug the other into the wall for power, like a phone charger.",
  },
  {
    title: "Then it quietly keeps watch.",
    body: "Every five minutes it checks your connection. Every hour it runs a full speed test. Every result is saved, so you have proof.",
  },
];

export const whyItMatters = {
  title: "Why it matters",
  body: "Internet providers tell you how fast your connection should be. The box shows how fast it really is.",
  reasons: [
    {
      icon: "/icons/record.webp",
      title: "It keeps a record",
      body: "A speed test on your phone shows one moment. The box checks all day and all night, so slow evenings and outages get written down too.",
    },
    {
      icon: "/icons/compare.webp",
      title: "Results you can compare",
      body: "It measures the same way as a University of Chicago study of home internet, so results from different homes and cities line up.",
    },
    {
      icon: "/icons/home.webp",
      title: "Advice for your home",
      body: "Later, we want to turn the results into personalized recommendations to improve your home's internet.",
      later: true,
    },
  ],
};

export const status = {
  title: "Where things stand",
  body: "The measuring software already runs on Mac and Linux, and we're still improving it. The box is next. Everything is free and open source, so anyone can see exactly how it works.",
};

export const DISCLAIMER =
  "An independent, personal project. It is not affiliated with, endorsed by or run by the City of New York, NYCHA, or any internet provider.";

// Questions people ask about the project, answered in plain words. They are
// shown on the page and published as FAQPage structured data, which must match.
export const faqs = [
  {
    question: "What is the Big Apple Connect Box?",
    answer:
      "A small, low-cost computer (a Raspberry Pi) that plugs into your router and measures your home internet all day, every day. It runs a quick check every five minutes and a full speed test every hour, and saves every result.",
  },
  {
    question: "What is Big Apple Connect?",
    answer:
      "Big Apple Connect is a New York City program that provides free internet to NYCHA residents. The city says it exists to ensure NYCHA residents have free, fast, reliable and safe internet.",
  },
  {
    question: "Is this project run by the City of New York or NYCHA?",
    answer:
      "No. It is an independent, personal project. It is not affiliated with, endorsed by or run by the City of New York, NYCHA, or any internet provider. It is named for the program it was built to measure.",
  },
  {
    question: "What does it measure?",
    answer:
      "Download and upload speed, ping to the router, the provider and the wider internet, name lookup times, the route out of the home, and Wi-Fi signal. It also records the setup: cable or Wi-Fi, the router and modem, and the provider.",
  },
  {
    question: "How is it different from a speed test on my phone?",
    answer:
      "A phone speed test shows one moment. The box checks around the clock, so slow evenings and outages are recorded too, and the results build into a record you can show to others.",
  },
  {
    question: "Can results be compared with other homes?",
    answer:
      "Yes. It measures the same way as Netrics, the open-source software used in the University of Chicago's home broadband study, so results from different homes and cities line up.",
  },
  {
    question: "Is it free, and can I try it now?",
    answer:
      "Yes. Everything is free and open source. The measuring program already runs on Mac and Linux, including Raspberry Pi, and can be downloaded from GitHub. The ready-to-plug-in box is next.",
  },
];
