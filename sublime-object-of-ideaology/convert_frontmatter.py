from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, "../.codex_deps")
sys.path.insert(0, "..")

import fitz  # type: ignore

from book_conversion_toolkit import (
    Heading,
    STANDARD_BOOK_CSS,
    image_file_to_data_uri,
    render_linked_contents,
    render_standard_nav,
    wrap_html_document,
)


PDF_PATH = Path("The Sublime Object of Ideology.pdf")
OUTPUT_PATH = Path("the-sublime-object-frontmatter.html")
FIGURE_DIR = Path("assets/figures")


FIGURES = {
    "graph-i": {
        "page": 141,
        "index": 0,
        "filename": "graph-i.png",
        "alt": "Graph I: lower level of the graph of desire",
        "caption": "Graph I",
    },
    "graph-ii": {
        "page": 144,
        "index": 0,
        "filename": "graph-ii.png",
        "alt": "Graph II: graph of desire with s(O), O, I(O), barred subject, signifier and voice",
        "caption": "Graph II",
    },
    "graph-iii": {
        "page": 154,
        "index": 0,
        "filename": "graph-iii.png",
        "alt": "Graph III: upper and lower levels of the graph of desire",
        "caption": "Graph III",
    },
    "completed-graph": {
        "page": 166,
        "index": 0,
        "filename": "completed-graph.png",
        "alt": "Completed graph of desire",
        "caption": "Completed Graph",
    },
    "encore-schema": {
        "page": 239,
        "index": 0,
        "filename": "encore-schema.png",
        "alt": "Lacanian schema linking Symbolic, Real, S(A), phi and jouissance",
        "caption": "Schema from Seminar Encore",
    },
}


FOOTNOTE_SCRIPT = """
(() => {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const closeLater = (wrap) => {
    clearTimeout(wrap._noteTimer);
    wrap._noteTimer = setTimeout(() => wrap.classList.remove('is-open'), 120);
  };
  document.querySelectorAll('.footnote-popover').forEach((wrap) => {
    const ref = wrap.querySelector('.note-ref');
    const note = wrap.querySelector('.floating-note');
    const open = (event) => {
      clearTimeout(wrap._noteTimer);
      wrap.classList.add('is-open');
      note.style.visibility = 'hidden';
      note.style.display = 'block';
      const width = note.offsetWidth || 340;
      const height = note.offsetHeight || 120;
      const source = event.type.startsWith('focus') ? ref.getBoundingClientRect() : null;
      const x = source ? source.left : event.clientX;
      const y = source ? source.bottom : event.clientY;
      const left = clamp(x - 16, 12, window.innerWidth - width - 12);
      const top = clamp(y + 14, 12, window.innerHeight - height - 12);
      note.style.setProperty('--note-left', `${left}px`);
      note.style.setProperty('--note-top', `${top}px`);
      note.style.visibility = '';
      note.style.display = '';
    };
    ref.addEventListener('mouseenter', open);
    ref.addEventListener('focusin', open);
    ref.addEventListener('mouseleave', () => closeLater(wrap));
    ref.addEventListener('focusout', () => closeLater(wrap));
    note.addEventListener('mouseenter', () => { clearTimeout(wrap._noteTimer); wrap.classList.add('is-open'); });
    note.addEventListener('mouseleave', () => closeLater(wrap));
  });
})();
""".strip()


FOOTNOTES = {
    1: "See Lee Smolin, The Trouble with Physics, New York: Houghton Mifflin Company, 2006.",
    2: "G. W. F. Hegel, Phenomenology of Spirit, Oxford: Oxford University Press, 1977, p. 455.",
    3: "G. W. F. Hegel, Science of Logic, London and New York: Humanities Press, 1976, p. 611.",
    4: "Hegel, Phenomenology of Spirit, p. 17.",
    5: "G. W. F. Hegel, Lectures on the Philosophy of Religion III, Berkeley: University of California Press, 1987, p. 127.",
    6: "Theodor W. Adorno, Negative Dialectics, New York: Continuum, 1973, p. 34.",
    7: "Hegel, Science of Logic, p. 841.",
    8: "Ibid., p. 843.",
    9: "G. W. F. Hegel, Philosophy of Mind, Oxford: Clarendon Press, 1971, Para. 381, p. 14.",
    10: "Catherine Malabou, The Future of Hegel, London: Routledge, 2005, p. 156.",
    11: "G. W. F. Hegel, Encyclopaedia of the Philosophical Sciences, Part I: Logic, Oxford: Oxford University Press, 1892, Par. 24.",
    12: "Hegel, The Science of Logic, p. 843.",
    13: "Hegel, Philosophy of Mind, Par. 57.",
    14: "See Alain Badiou, L'Être et l'événement, Paris: Editions de Minuit, 1989.",
}


INTRO_FOOTNOTES = {
    1: "For example, see Foucault, Power/Knowledge, New York: The Harvester Press, 1980.",
    2: "Louis Althusser, For Marx, London: Verso, 2006.",
    3: "Michel Pêcheux, Language, Semantics and Ideology, New York: Macmillan, 1982.",
    4: "See Herbert Marcuse, Eros and Civilization, Boston, MA: Beacon Press, 1974.",
}


CHAPTER_ONE_FOOTNOTES = {
    1: "Hans Jürgen Eysenck, Sense and Nonsense in Psychology, Harmondsworth: Penguin, 1966.",
    2: "Sigmund Freud, The Interpretation of Dreams, Harmondsworth: Penguin, 1977.",
    3: "Ibid., p. 446.",
    4: "Ibid., p. 650.",
    5: "Karl Marx, Capital, Volume I, Harmondsworth: Penguin, 1976, p. 168.",
    6: "Ibid., p. 76.",
    7: "Alfred Sohn-Rethel, Intellectual and Manual Labour, London: Macmillan, 1978, p. 31.",
    8: "Ibid., p. 33.",
    9: "Ibid., p. 59.",
    10: "Ibid., p. 59.",
    11: "Ibid., p. 42.",
    12: "Ibid., pp. 26-7.",
    13: "Jacques Lacan, 'RSI', Ornicar? 4, p. 106.",
    14: "Marx, Capital, Volume I, p. 77.",
    15: "Ibid., p. 59.",
    16: "Ibid., p. 63.",
    17: "'Lordship' and 'bondage' are the terms used in the translation we refer to (Hegel, Phenomenology of Spirit); following Kojève, Lacan uses 'maître' and 'esclave', which are then translated as 'master' and 'slave'.",
    18: "Marx, Capital, Volume I, p. 82.",
    19: "Jacques Lacan, Le séminaire VII: L'éthique de la psychanalyse, Paris: Seuil, 1986, p. 231.",
    20: "Karl Marx, Les 'sentiers escarpés' de Karl Marx, Volume I, Paris: CERF, 1977, p. 132.",
    21: "Lacan, Le Séminaire VII, p. 295.",
    22: "Blaise Pascal, Pensées, Harmondsworth: Penguin, 1966, p. 274.",
    23: "Ibid., p. 46.",
    24: "Ibid., p. 216.",
    25: "Franz Kafka, The Trial, Harmondsworth: Penguin, 1985, p. 243.",
    26: "Pascal, Pensées, pp. 152-3.",
    27: "Louis Althusser, Essays on Ideology, London: Verso, 1984.",
    28: "Freud, The Interpretation of Dreams, p. 652.",
    29: "Jacques Lacan, The Four Fundamental Concepts of Psycho-Analysis, Harmondsworth: Penguin, 1979, chapters 5 and 6.",
    30: "Ibid., Chapter 6.",
}


CHAPTER_TWO_FOOTNOTES = {
    1: "Jacques Lacan, The Seminar of Jacques Lacan, Book I: Freud's Papers on Technique, Cambridge: Cambridge University Press, 1988, p. 159.",
    2: "Ibid., p. 158.",
    3: "Lacan, The Four Fundamental Concepts of Psycho-Analysis, p. 26.",
    4: "Freud, The Interpretation of Dreams, p. 559.",
    5: "G. W. F. Hegel, Vorlesungen über die Philosophie der Geschichte, Frankfurt: Suhrkamp Verlag, 1969, pp. 111-13.",
    6: "Kafka, The Trial, p. 237.",
    7: "Robert A. Heinlein, The Door into Summer, New York: Del Rey, 1986, p. 287.",
    8: "Walter Lord, A Night to Remember, New York: Bantam, 1983, pp. xi-xii.",
    9: "Jacques Lacan, 'Joyce le symptôme', in Joyce avec Lacan, Paris: Navarin Editeur, 1987.",
    10: "Franz Kafka, Wedding Preparations in the Country and Other Stories, Harmondsworth: Penguin, 1978, p. 122.",
    11: "Lacan, The Four Fundamental Concepts of Psycho-Analysis, Chapter 10.",
    12: "Jacques Lacan, Écrits, Paris: Seuil, 1966.",
    13: "René Descartes, Discourse on Method, Harmondsworth: Penguin, 1976, p. 64.",
    14: "Jon Elster, Sour Grapes, Cambridge: Cambridge University Press, 1982, p. 96.",
}


CHAPTER_THREE_FOOTNOTES = {
    1: "Saul Kripke, Naming and Necessity, Cambridge, MA: Harvard University Press, 1980, pp. 83-5.",
    2: "Ibid., p. 119.",
    3: "Ibid., p. 24.",
    4: "John Searle, Intentionality, Cambridge: Cambridge University Press, 1984, p. 240.",
    5: "Ibid., p. 259.",
    6: "Ibid., p. 252.",
    7: "See Jacques Lacan, 'Subversion of the Subject and the Dialectic of Desire', Écrits: A Selection, New York: W. W. Norton, 1977.",
    8: "For propaedeutic reasons, we use in this chapter the English transcription of Lacan's mathemes (O, not A, etc.).",
    9: "Jacques-Alain Miller, 'Les Réponses du réel', in Aspects du malaise dans la civilisation, Paris: Navarin, 1987, p. 21.",
    10: "Jacques Lacan, Le Séminaire III: Les psychoses, Paris: Seuil, 1981, p. 315.",
    11: "The other achievement of the film is the final rehabilitation of Judas as the real tragic hero of this story: he was the one whose love for Christ was the greatest, and it was for this reason that Christ considered him strong enough to fulfil the horrible mission of betraying him, thus assuring the accomplishment of Christ's destiny (the Crucifixion).",
    12: "Bernard Baas, 'Le désir pur', Ornicar? 43, 1987.",
    13: "Here we could use the distinction elaborated by Kovel (White Racism, London: Free Association Books, 1988) between dominative and aversive racism.",
}


CHAPTER_FOUR_FOOTNOTES = {
    1: "Miran Božovič, 'Immer Ärger mit dem Körper', Wo es war 5-6, Ljubljana-Vienna, 1988.",
    2: "Walter Benjamin, Illuminations, New York: Schocken, 1969, p. 253.",
    3: "Freud, The Interpretation of Dreams, p. 178.",
    4: "Jacques Lacan, The Seminar of Jacques Lacan, Book I: Freud's Papers on Technique, Cambridge: Cambridge University Press, 1988, p. 243.",
    5: "Walter Benjamin, Gesammelte Schriften, Volume I, Frankfurt: Suhrkamp Verlag, 1955, p. 1238.",
    6: "Lacan, The Seminar of Jacques Lacan, Book I, p. 159.",
    7: "Jacques Lacan, Le Séminaire XX: Encore, Paris: Seuil, 1975, p. 52.",
    8: "Ernst Kantorowicz, The King's Two Bodies, Princeton, NJ: Princeton University Press, 1959; Rado Riha, 'Das Dinghafte der Geldware', Wo es war 1, Ljubljana-Vienna, 1986.",
    9: "Claude Lefort, L'Invention démocratique, Paris: Fayard, 1981.",
}


CHAPTER_FIVE_FOOTNOTES = {
    1: "Jürgen Habermas, The Philosophical Discourse of Modernity, Cambridge: Cambridge University Press, 1988.",
    2: "Jacques Derrida, The Post Card: From Socrates to Freud and Beyond, Chicago: Chicago University Press, 1987.",
    3: "Otto Fenichel, 'Die \"lange Nase\"', Imago 14, Vienna, 1928.",
    4: "Jacques Lacan, The Four Fundamental Concepts of Psycho-Analysis, Harmondsworth: Penguin, 1979, Chapter 16.",
    5: "Jean-Luc Nancy and Philippe Lacoue-Labarthe, Le Titre de la lettre, Paris: Galilée, 1973.",
    6: "Jacques Lacan, The Seminar of Jacques Lacan, Book I, Cambridge: Cambridge University Press, 1988, Chapter 22.",
    7: "Lacan, Écrits, pp. 765-6.",
    8: "F. W. J. Schelling, Über das Wesen der menschlichen Freiheit, Frankfurt: Suhrkamp Verlag, 1978, pp. 78-9.",
    9: "Lacan, Le séminaire XX: Encore, p. 85.",
    10: "Michel Silvestre, Demain la psychanalyse, Paris: Navarin, 1988.",
    11: "Theodor W. Adorno, 'Society', Salmagundi 10-11, 1970.",
    12: "Lacan, The Seminar of Jacques Lacan, Book I, p. 265.",
    13: "Jacques-Alain Miller, 'Les Réponses du réel', in Aspects du malaise dans la civilisation, Paris: Navarin, 1987.",
    14: "Franz Kafka, The Trial, Harmondsworth: Penguin, 1985, p. 251.",
    15: "Ibid., p. 47.",
    16: "Mladen Dolar, 'Hitchcock's Objekt', Wo es war 1, Ljubljana-Vienna, 1986.",
    17: "Lacan, Le Séminaire XX: Encore, p. 83.",
    18: "Rastko Močnik, 'Ueber die Bedeutung der Chimären für die conditio humana', Wo es war 1, Ljubljana-Vienna, 1986.",
    19: "Mladen Dolar, 'Die Einführung in das Serail', Wo es war 3-4, Ljubljana-Vienna, 1987.",
    20: "Hegel, Phenomenology of Spirit, p. 47.",
    21: "Ibid., p. 89.",
    22: "Ibid., pp. 88-9.",
    23: "Lacan, The Four Fundamental Concepts of Psycho-Analysis, Harmondsworth: Penguin, 1979, p. 103.",
    24: "Hegel, Phenomenology of Spirit, p. 103.",
    25: "Lacan, The Four Fundamental Concepts of Psycho-Analysis, p. 112.",
}


CHAPTER_SIX_FOOTNOTES = {
    1: "Yirmiyahu Yovel, 'La Religion de la sublimité', in Hegel et la religion, ed. G. Planty-Bonjour, Paris: PUF, 1982.",
    2: "Immanuel Kant, Critique of Judgement, Oxford: Clarendon Press, 1964, p. 109.",
    3: "Ibid., p. 119.",
    4: "Ibid., p. 106.",
    5: "Ibid., p. 127.",
    6: "Hegel, Phenomenology of Spirit, p. 195.",
    7: "Ibid., p. 210.",
    8: "Ibid., p. 310.",
    9: "Ibid., p. 308.",
    10: "G. W. F. Hegel, Wissenschaft der Logik, volumes I and II, Hamburg: Hg. von G. Lasson, 1966.",
    11: "Hegel, Phenomenology of Spirit, p. 385.",
    12: "Ibid., pp. 270-1.",
    13: "G. W. F. Hegel, Philosophie der Religion, volumes I and II, Frankfurt: Suhrkamp Verlag, 1969.",
    14: "G. W. F. Hegel, Grundlinien der Philosophie des Rechts, Frankfurt: Suhrkamp Verlag, 1969, Paragraph 280.",
    15: "Dieter Henrich, Hegel im Kontext, Frankfurt: Suhrkamp Verlag, 1971.",
}


REPLACEMENTS = {
    "SLAVOJ ZrZEK": "SLAVOJ ŽIŽEK",
    "PrifO.ce": "Preface",
    "XXlll": "xxiii",
    "which Subject": "Which Subject",
    "ofPtolemization": "of Ptolemization",
    "The Sublime Object o/\"Ideology": "The Sublime Object of Ideology",
    "SClence": "science",
    "AtifhebuI{9\"l": "Aufhebung",
    "Atifhebu118": "Aufhebung",
    "Azifhebung": "Aufhebung",
    "Arifhebung": "Aufhebung",
    "fIxed": "fixed",
    "fIXed": "fixed",
    "mortifyingjob": "mortifying job",
    "ofLife": "of Life",
    "trot": "not",
    "unifYing": "unifying",
    "ourUnderstanding": "our Understanding",
    "power of'tearing": "power of 'tearing",
    "offive": "of five",
    "'neously": "neously",
    "O!:tite": "Quite",
    "oflivelj": "of lively",
    "spin'tualfy": "spiritually",
    "Ie trait unaire": "le trait unaire",
    "Zll8": "Zug",
    "M6glichkeitgeti(gte Wirklichkeiz": "Möglichkeit getilgte Wirklichkeit",
    "zur Moglichkeit getilgte Wirklichkeit": "zur Möglichkeit getilgte Wirklichkeit",
    "signifjring": "signifying",
    "thi,¥!": "thing",
    "fulfy": "fully",
    "signifYing": "signifying",
    "potentiaL": "potential",
    "If!": "If I",
    "myself That": "myself. That",
    "mysel£": "myself",
    "sul?jectille": "subjective",
    "evel)'thi1l8 within itse!f/": "everything within itself",
    "[Aufhebung of": "[Aufhebung] of",
    "philosop/yl of Mind": "Philosophy of Mind",
    "philosop» ofMlild": "Philosophy of Mind",
    "Science ojLogic": "Science of Logic",
    "PhellomellologyofSpin't": "Phenomenology of Spirit",
    "cOIle/usioll": "conclusion",
    "philosoplfy": "philosophy",
    "atifheben": "aufheben",
    "befteien": "befreien",
    "Azifhebung s": "Aufhebung's",
    "Aufhebung s": "Aufhebung's",
    "ofsublation": "of sublation",
    "sublatioll": "sublation",
    "ifHI!el": "of Hegel",
    "itselE": "itself",
    "begrif fin": "begriffen",
    "Ziltun": "Zutun",
    "suiject's fieedom is to setfiee its ofjea": "subject's freedom is to set free its object",
    "Eng'dopaedia of the philosophical Sciellces": "Encyclopaedia of the Philosophical Sciences",
    "nature.l2": "nature",
    "subjectivity.l]": "subjectivity",
    "poinr": "point",
    "recognized' as such'": "recognized 'as such'",
    ":.let": ": let",
    "Anselin's": "Anselm's",
    "ofj being": "of) being",
    "realfy": "really",
    "\u083fet": "let",
    "foIl": "fail",
    "foil": "fail",
    "p£l.f-tou": "pas-tout",
    "L '!tre et /'fvenement": "L'Être et l'événement",
    "of , System'": "of 'System'",
    "setfiee": "set free",
    "ofitsel£": "of itself",
    "Par. 57": "Par. 57",
    "posit ively": "positively",
    "si࠰ple": "simple",
    "take away}": "take away']",
    "ifby": "if by",
    "itselfin": "itself in",
    "insist's": "insists",
    "sul?ject": "subject",
    "universalj": "universal)",
    "order of'coliectivi!J:": "order of 'collectivity',",
    "berween": "between",
    "Dialectic ofEnlightenment": "Dialectic of Enlightenment",
    "itselfits own nomination among": "itself - its own nomination - among",
    "medium of, grey'": "medium of 'grey'",
    "inner potential When": "inner potential. When",
    "Hegel writes, If": "Hegel writes: If",
    "fimdamentally": "fundamentally",
    "begriffin": "begriffen",
    "selfdevelopment": "self-development",
    "itselfj": "itself)",
    "Idea' decides'": "Idea 'decides'",
    "out of itself Here": "out of itself. Here",
    "conditionsdeterminations": "conditions-determinations",
    "met(and": "met (and",
    "Things. 'materially exist'": "Things 'materially exist'",
    "(pas-tout of truth": "(pas-tout) of truth",
    "excrementationexternalization": "excrementation-externalization",
    "processwith-a-subject": "process-with-a-subject",
    "Haber mas": "Habermas",
    "Modeme": "Moderne",
    "LeviStrauss": "Levi-Strauss",
    "P/cheux": "Pêcheux",
    "Pळcheux": "Pêcheux",
    "Lal18ul1fje, Semalltia alld Ideology": "Language, Semantics and Ideology",
    "cider sur son dfsir": "céder sur son désir",
    "evety": "every",
    "We stern": "Western",
    "Ladau": "Laclau",
    "Heaemof9! and Soa'alist Strategy": "Hegemony and Socialist Strategy",
    "impossill!J": "impossibility",
    "atrempt": "attempt",
    "Soaalist": "Socialist",
    "ofLacan": "of Lacan",
    "Lac an": "Lacan",
    "Lac ani an": "Lacanian",
    "assum ing": "assuming",
    "wellknown": "well-known",
    "selfmediation": "self-mediation",
    "art ofliving": "art of living",
    "subject-cause": "subject-cause",
    "socalled": "so-called",
    "discussions ofBataille": "discussions of Bataille",
    "HabermasFoucault": "Habermas-Foucault",
    "another debate'": "another debate",
    "Althusser -Lacan": "Althusser-Lacan",
    "philosophy-of-Ianguage": "philosophy-of-language",
    "notion of, alienation'": "notion of 'alienation'",
    "notion of, alienation": "notion of 'alienation",
    "circuit of'no": "circuit of 'no",
    "more. precisely": "more precisely",
    "ParsifaL": "Parsifal",
    "We have; for example": "We have, for example",
    "Psychoanalytic' essentialism": "Psychoanalytic 'essentialism'",
    "plutality": "plurality",
    "Hegel dixit-'an": "Hegel dixit - 'an",
    "maSs": "mass",
    "opposire": "opposite",
    "democracy itself Here": "democracy itself. Here",
    "not'radical'": "not 'radical'",
    "imposill!J": "impossibility",
    "Ie plus sublime des Iy;steriques": "Le plus sublime des hystériques",
    "suturɣd": "sutured",
    "Hegel' s": "Hegel's",
    "... 'This": "... ' This",
    "Lacani an": "Lacanian",
    "Ie point de capitan": "le point de capiton",
    "surplusenjoyment": "surplus-enjoyment",
    "post modernist": "postmodernist",
    "Psychoanalytic 'essentialism''": "Psychoanalytic 'essentialism'",
    "self Here": "self. Here",
    "Of course, the philosophy": "of course, the philosophy",
    "Of course, the break": "of course, the break",
    "Of course, we have": "Of course, we have",
    "mouth of Parsifal": "mouth of Parsifal.",
    "accepts' contradiction'": "accepts 'contradiction'",
    "... 'This": "... ' This",
    "field of, post-structuralism'": "field of 'post-structuralism'",
    "post modernist": "postmodernist",
    "How D id Marx Invent the Sym ptom": "How Did Marx Invent the Symptom",
    "ana!JIsis afform": "analysis of form",
    "secret' afthis": "secret of this",
    "Hans-Jiirgen": "Hans-Jürgen",
    "dream ofIrma": "dream of Irma",
    "treatment ofIrma": "treatment of Irma",
    "obviously. neither": "obviously neither",
    "dreamthought": "dream-thought",
    "confers 011": "confers on",
    "dream-thoUfJhtò": "dream-thoughts'",
    "oHhought": "of thought",
    "Urverdriingung": "Urverdrängung",
    "Ullconsa\"ous": "unconscious",
    "contȀnt": "content",
    "commodity-form itsel£": "commodity-form itself",
    "itself The": "itself. The",
    "oJthe commodi9'-Jorm": "of the commodity-form",
    "pn'mafacie": "prima facie",
    "fOIms": "forms",
    "efctivity": "effectivity",
    "as fthe": "as if the",
    "as fit": "as if it",
    "as ifit": "as if it",
    "matenal": "material",
    "flnn": "form",
    "ofthou,ght": "of thought",
    "thou,ght": "thought",
    "doma,in": "domain",
    "difined 0/": "defined by",
    "fIssure": "fissure",
    "notaware": "not aware",
    "ve!y": "very",
    "consisten9'": "consistency",
    "reali!J": "reality",
    "°mptom": "symptom",
    "withoutits": "without its",
    "inter nal": "internal",
    "para doxical": "paradoxical",
    "bri118s": "brings",
    "Capita/'": "Capital,",
    "oftike": "of the",
    "Paut": "Paul",
    "hirnselfin": "himself in",
    "effectofinversion": "effect of inversion",
    "as ifB": "as if B",
    "alreatfy in itseffbe": "already in itself be",
    "beingan-equivalent": "being-an-equivalent",
    "offetishism": "of fetishism",
    "Ilot'fetishized": "not 'fetishized",
    "parmer": "partner",
    "satisfY": "satisfy",
    "rotally": "totally",
    "capiralism": "capitalism",
    "products oflabour": "products of labour",
    "9'nical": "Cynical",
    "vain -the": "vain - the",
    "lall8hter": "laughter",
    "jOlm ofideology": "form of ideology",
    "fantll9'": "fantasy",
    "rfbelief": "of belief",
    "oijectivefy": "objectively",
    "p.)lcoanafysis": "psychoanalysis",
    "Ka£ka": "Kafka",
    "ojAlthusser": "of Althusser",
    "Pascali an": "Pascalian",
    "unconsdousfy": "unconsciously",
    "inter pellation": "interpellation",
    "ofZhuang": "of Zhuang",
    "FantQ!)' as a support if reali!y": "Fantasy as a support of reality",
    "surplus-e'!ioyment": "surplus-enjoyment",
    "Concepts o/PZcho-Anafysis": "Concepts of Psycho-Analysis",
    "Concepts I!fPsycho Anafysis": "Concepts of Psycho-Analysis",
    "reproachfolfy": "reproachfully",
    "ann and": "arm and",
    "authonjy": "authority",
    "t1th": "truth",
    "tralliferellce": "transference",
    "affiiction": "affliction",
    "concern ing": "concerning",
    "pro blem": "problem",
    "intro ductory": "introductory",
    "exemplifY": "exemplify",
    "artic ulated": "articulated",
    "figu ration": "figuration",
    "equalobstinacy": "equal obstinacy",
    "latent dream thoughts": "latent dream-thoughts",
    "product oflabour": "product of labour",
    "itsel£": "itself",
    "UllCOnsa\"OUS": "unconscious",
    "óctive": "effective",
    "das reale AbstraktionJ": "die reale Abstraktion]",
    "usevalue": "use-value",
    "SohnRethel": "Sohn-Rethel",
    "The Ethic ofP!JIchoanafysis": "The Ethic of Psychoanalysis",
    "Four Fundamental Concepts ofP!),choanafysis": "Four Fundamental Concepts of Psycho-Analysis",
    "far.from hinderil18 the fail submission 0/": "far from hindering the full submission of",
    "condition o/it": "condition of it",
    "ideologicaljouis-sense": "ideological jouis-sense",
    "avant la lewe": "avant la lettre",
    "appa ratus": "apparatus",
    "bifore": "before",
    "su/vectivation": "subjectivation",
    "su/v'ectivation": "subjectivation",
    "awak ening": "awakening",
    "gener alized": "generalized",
    "onfy": "only",
    "tile Real": "the Real",
    "nothil18 but a cOl1sdOUSI1e5S": "nothing but a consciousness",
    "totali[Y": "totality",
    "totality seton ifciT18 the tracesofits own impossibili[Y": "totality setting effacing the traces of its own impossibility",
    "totality seton ifciT18 the tracesofits own impossibility": "totality setting effacing the traces of its own impossibility",
    "differ ence": "difference",
    "folse' etemalization": "false eternalization",
    "universalization:.": "universalization:",
    "cধndition": "condition",
    "histon\"cization": "historicization",
    "ptovided": "provided",
    "ifit": "if it",
    "butter fy": "butterfly",
    "dream ing": "dreaming",
    "offantasy": "of fantasy",
    "inter subjective": "intersubjective",
    "ideol- 0gy": "ideology",
    "neigh bour": "neighbour",
    "of'ideology'": "of 'ideology'",
    "partidpants": "participants",
    "repro duction": "reproduction",
    "defi nitions": "definitions",
    "'Ideolo8ical'is not the false consdousness' ofa (soda/) bein8 but this beil18 itse!fin so.far as it is supported f?y Jalse consa\"ousnes": "'Ideological' is not the 'false consciousness' of a (social) being but this being itself in so far as it is supported by 'false consciousness'.",
    "The sodal!JImptom": "The social symptom",
    "reference ro": "reference to",
    "The Semillar of jacques LacalZ": "The Seminar of Jacques Lacan",
    "Papers 011 Techllique": "Papers on Technique",
    "symp tom": "symptom",
    "symp toms": "symptoms",
    "signi fier": "signifier",
    "signi fier's": "signifier's",
    "signifY": "signify",
    "নther": "Other",
    "rf - as Lacan": "If - as Lacan",
    "rwenty-fifth": "twenty-fifth",
    "alwqys": "always",
    "shepP9'": "Sheppey'",
    "misrecog nition": "misrecognition",
    "Morniel": "Mordiel",
    "at *e right": "at the right",
    "Here; in": "Here, in",
    "strength ened": "strengthened",
    "accor dance": "accordance",
    "Wq,Y": "way",
    "thaJ": "that",
    "histor ical": "historical",
    "percep tion": "perception",
    "expres sion": "expression",
    "independ ently": "independently",
    "non symbolized": "non-symbolized",
    "Repetition in Histo!y": "Repetition in History",
    "Laean": "Lacan",
    "wordplay-translation ofUnbewusste": "wordplay-translation of Unbewusste",
    "necessanfy": "necessarily",
    "plzilosoply; of the Law": "Philosophy of Right",
    "plzilosoply;": "Philosophy",
    "full offaIse jines-sf": "full of false finesse",
    "thry do not": "they do not",
    "tl are doin,g": "they are doing",
    "ofbasic": "of basic",
    "offaIse": "of false",
    "of'knot": "of 'knot",
    "Titanicas": "Titanic as",
    "sttuggling": "struggling",
    "some how": "somehow",
    "Futiliry": "Futility",
    "knoথs": "knots",
    "April 1 0": "April 10",
    "Rubajyat ojOmar": "Rubaiyat of Omar",
    "Titanid": "Titanic",
    "diffi cult": "difficult",
    "phenom enon": "phenomenon",
    "jouis-sanee": "jouissance",
    "jouiiJ": "jouir",
    "mllst": "must",
    "fulftlment": "fulfilment",
    "oijet petit": "objet petit",
    "Mussolilli": "Mussolini",
    "meaning ofit": "meaning of it",
    "proper t o": "proper to",
    "of'states": "of 'states",
    "development. '4": "development. '4",
    "ifct": "effect",
    "spoilt It": "spoilt. It",
    "beliefin": "belief in",
    "justifJ": "justify",
    "sOfi!,ewhere": "somewhere",
    "ofideology": "of ideology",
    "Sinthom£": "Sinthome",
    "as!,Ymptom": "as Symptom",
    "the!Jmptom": "the symptom",
    "ldennfication": "Identification",
    "forma tion": "formation",
    "inyou more than yourseff": "In you more than yourself",
    "wiOless": "witness",
    "repre senting": "representing",
    "clarkin": "dark in",
    "fasOless": "fastness",
    "Parsjfol": "Parsifal",
    "Arnfortas": "Amfortas",
    "At frst": "At first",
    "terri£Ying": "terrifying",
    "hisgannent": "his garment",
    "woundl": "wound!",
    "enjoy ment": "enjoyment",
    "a!JImbolic": "a symbolic",
    "anni hilate": "annihilate",
    "A lien": "Alien",
    "ofAmfortas": "of Amfortas",
    "external ized": "externalized",
    "allamorphicstatus": "anamorphic status",
    "pour ing": "pouring",
    "sillthome": "sinthome",
    "Ideologicaljouissance": "Ideological jouissance",
    "resSeTltimellt": "ressentiment",
    "Ecrits": "Écrits",
    "dell9'": "delay",
    "ob9'l": "obey!",
    "offantCl9'": "of fantasy",
    "wt9'": "way",
    "nameftom": "name from",
    "newspapel": "newspaper",
    "Tn·a!": "Trial",
    "aU authority": "all authority",
    "Truth and Other fniomas": "Truth and Other Enigmas",
    "subjective illusionj perception": "subjective illusion, a perception",
    "inde pendently": "independently",
    "onto logical": "ontological",
    "gentrifY": "gentrify",
    "Titanic. of course": "Titanic. Of course",
    "micro cosm": "microcosm",
    "in vested": "invested",
    "to day's": "today's",
    "over determination": "overdetermination",
    "offascination": "of fascination",
    "impossiblejouirsance": "impossible jouissance",
    "ofjouirsance": "of jouissance",
    "jouis sense": "jouis-sense",
    "From!ymptom to sinthome": "From symptom to sinthome",
    "consis tency": "consistency",
    "VerweifUng": "Verwerfung",
    "offoreclosure": "of foreclosure",
    "point de capitan": "point de capiton",
    "Name-of-theFather": "Name-of-the-Father",
    "form ofhallu cinatory": "form of hallucinatory",
    "propo symptom': woman": "proposition 'woman is a symptom': woman",
    "identifi!J": "identity",
    "identi!J": "identity",
    "ofits": "of its",
    "fLXes": "fixes",
    "detetmined": "determined",
    "fiminism": "feminism",
    "division oflabour": "division of labour",
    "pOlizts de capiton": "points de capiton",
    "freefloating": "free-floating",
    "srate": "state",
    "democraticegalitarian": "democratic-egalitarian",
    "a: hegemonic": "a hegemonic",
    "vicrory": "victory",
    "essen tialism": "essentialism",
    "bocfy": "body",
    "sciencefiction": "science-fiction",
    "BOtfy": "Body",
    "auswer": "answer",
    "inten tional": "intentional",
    "difrence": "difference",
    "Idemi9'": "Identity",
    "HegemonyandSocialistStrategy": "Hegemony and Socialist Strategy",
    "pro toideological": "proto-ideological",
    "Desmptivism": "Descriptivism",
    "antidesmptivism": "antidescriptivism",
    "Namifl andNecessiry": "Naming and Necessity",
    "83 5": "83-5",
    "identifY": "identify",
    "aU the more": "all the more",
    "a8eneral": "a general",
    "ofcommunication": "of communication",
    "theO!JI": "theory",
    "liltelltiollah[y": "Intentionality",
    "The two 'o/ths": "The two myths",
    "aucial": "crucial",
    "mastersignifier": "master-signifier",
    "mastersignifiers": "master-signifiers",
    "ol?jet": "objet",
    "Retroactivi!J' of meani11lJ": "Retroactivity of Meaning",
    "sur£.1.ces": "surfaces",
    "marked૩": "marked Δ",
    "<:Jut": "out",
    "ofic": "of it",
    "interpeUates": "interpellates",
    "temember": "remember",
    "£act": "fact",
    "The 'efct of retroversion J": "The 'effect of retroversion'",
    "'ehe vuoi?'": "'Che vuoi?'",
    "Fairs. he": "Écrits. He",
    "chat all": "that all",
    "fIx U": "fix it.",
    "eke vuoi": "che vuoi",
    "sqyins": "saying",
    "nOllj'ustified": "non-justified",
    "ofhystericization": "of hystericization",
    "The Last Temptation 0/ Christ": "The Last Temptation of Christ",
    "/yJstendzation ojjesus christ": "hystericization of Jesus Christ",
    "Onzicar": "Ornicar",
    "Les desir pur": "Le désir pur",
    "i࠭ a mediator": "is a mediator",
    "frameworkof": "framework of",
    "] ames": "James",
    "o/Jouissance": "of Jouissance",
    "Goi\"8 through": "Going through",
    "socialfontasy": "social fantasy",
    "dn've": "drive",
    "dosed": "closed",
    "social negativi!JI": "social negativity",
    "dearly a social": "clearly a social",
    "except theJews": "except the Jews",
    "untest": "unrest",
    "You O n ly Die Twice": "You Only Die Twice",
    "atticulation": "articulation",
    "Field oj Speech": "Field of Speech",
    "Language... J": "Language...]",
    "thing itselfis": "thing itself is",
    "concept oflanguage": "concept of language",
    "fa signification": "la signification",
    "morti£Ying": "mortifying",
    "The Ethic ofPsychoanafysis": "The Ethic of Psychoanalysis",
    "ofJacques-Alain": "of Jacques-Alain",
    "parcle pleine": "parole pleine",
    "juliette": "Juliette",
    "death -the": "death - the",
    "forms oflife": "forms of life",
    "body.' Today": "body. Today",
    "!J'mbolic": "symbolic",
    "ofsymbolization": "of symbolization",
    "philosopl!)' 0/ Histol)'": "Philosophy of History",
    "w:as": "was",
    "Benjamin' s": "Benjamin's",
    "g3,me": "game",
    "Eil1gedenken": "Eingedenken",
    "oneselfin": "oneself in",
    "itselfis": "itself is",
    "his tor ical": "historical",
    "revolurionary": "revolutionary",
    "ofMarivaux": "of Marivaux",
    "efEtced": "effaced",
    "come's": "comes",
    "LastJudgement": "Last Judgement",
    "notion ofhistory": "notion of history",
    "finতl": "final",
    "Humanism and TeITor": "Humanism and Terror",
    "funda mental": "fundamental",
    "Lacan's,.from": "Lacan's, from",
    "Ethic ofP9ldioanafysis": "Ethic of Psychoanalysis",
    "main taining": "maintaining",
    "regis tration": "registration",
    "Ninotclzka": "Ninotchka",
    "exacdy": "exactly",
    "personi£Ying": "personifying",
    "La Boetie": "La Boétie",
    "classical\" Master": "classical Master",
    "difines": "defines",
    "demo cratic": "democratic",
    "place ofpower": "place of power",
    "su,?jects": "subjects",
    "surrogare": "surrogate",
    "total itarianism": "totalitarianism",
    "imme diate": "immediate",
    "quanti tative": "quantitative",
    "mechanisণ": "mechanism",
    "Theol)' r/Fictions": "Theory of Fictions",
    "oflanguage": "of language",
    "Poe' s": "Poe's",
    "mortifYing": "mortifying",
    "kerneL": "kernel",
    "fontasme": "fantasme",
    "ReaL": "Real",
    "Interpretation ojDreams": "Interpretation of Dreams",
    "oflack": "of lack",
    "histOlY": "history",
    "non-histoncalplace": "non-historical place",
    "inso far": "in so far",
    "0/ placing": "of placing",
    "totali9'": "totality",
    "ofsignification": "of signification",
    "/lOll": "non",
    "Stalini࠮m": "Stalinism",
    "evolutional)'": "evolutionary",
    "measqred": "measured",
    "deaȥh": "death",
    "anihilo": "ex nihilo",
    "apocafypse": "apocalypse",
    "ifhe": "if he",
    "Seminar oल The Ethic q{Psychoallafysis": "Seminar on The Ethic of Psychoanalysis",
    "evolutionalJ'": "evolutionary",
    "[re)production": "(re)production",
    "starts ro constrict": "starts to constrict",
    "t/zis very immanent limit": "this very immanent limit",
    "'internal contradiction΢": "'internal contradiction',",
    "continuity ofprogress": "continuity of progress",
    "Atif/zebung": "Aufhebung",
    "IX nihilo": "ex nihilo",
    "himsel£": "himself",
    "post structuralism": "post-structuralism",
    "pointdecapiton": "point de capiton",
    "Lac an": "Lacan",
    "smoothlY": "smoothly",
    "meta physical": "metaphysical",
    "conven ient": "convenient",
    "inter textual": "intertextual",
    "decentted": "decentred",
    "afcted": "affected",
    "clearfy": "clearly",
    "whichgives body": "which gives body",
    "JUndamental": "fundamental",
    "pwence": "presence",
    "NaseJ": "Nase]",
    "ifthat,you": "of that, you",
    "imitaring": "imitating",
    "somethi11!f": "something",
    "la11!fua8e": "language",
    "110 la11!fuage": "no language",
    "olject": "object",
    "Lacan' s": "Lacan's",
    "tide": "title",
    "Vorstellungsrepriisentanz": "Vorstellungsrepräsentanz",
    "Vorstellullgsrepriisentanz": "Vorstellungsrepräsentanz",
    "Vorstellunasrepriiselltanz": "Vorstellungsrepräsentanz",
    "Vorstellunal": "Vorstellung",
    "difrence": "difference",
    "su૫ject": "subject",
    "signifjing": "signifying",
    "AntU[Jollism": "Antagonism",
    "irifinitum": "infinitum",
    "subjet suppose saJloir": "sujet supposé savoir",
    "Fiatjustitia": "Fiat justitia",
    "1950S": "1950s",
    "1970S": "1970s",
    "the!Jmbolic": "the symbolic",
    "Imaginal)!": "Imaginary",
    "subject/ but": "subject, but",
    "ifit": "if it",
    "U/lSeres": "unseres",
    "ɛmposium": "Symposium",
    "Akibiades": "Alcibiades",
    "horrifjring": "horrifying",
    "jouiITance": "jouissance",
    "jOuisance": "jouissance",
    "atrracts": "attracts",
    "subjectivatiolt": "subjectivation",
    "subjec tivation": "subjectivation",
    "The TnalJosefK.": "The Trial Josef K.",
    "alrearfy": "already",
    "S(I), a, ifJ": "S(Ⱥ), a, $",
    "Thir9'-Nine": "Thirty-Nine",
    "Latfy": "Lady",
    "MUch": "Much",
    "symbo lically": "symbolically",
    "hnaginary": "Imaginary",
    "jOuissance": "jouissance",
    "dearly": "clearly",
    "transfirence": "transference",
    "knowledse": "knowledge",
    "Correspolldent": "Correspondent",
    "ill the ve'Y fonn": "in the very form",
    "ve!y nzelotfy": "very melody",
    "recondl iation": "reconciliation",
    "isalreatfy": "is already",
    "alreatfy": "already",
    "fiar if error": "fear of error",
    "itse!/,": "itself'",
    "phellOl1lello{ogy": "Phenomenology",
    "Do/s tfthe": "Days of the",
    "forward ro the": "forward to the",
    "enables us ro recognize": "enables us to recognize",
    "alreatfy": "already",
    "trompe {'reil": "trompe l'oeil",
    "therifore": "therefore",
    "o૧ectiveThings": "objective things",
    "emp9'": "empty",
    "vOId": "void",
    "po૨itive": "positive",
    "olljects": "objects",
    "L 'We d'or": "L'Âge d'or",
    "Cnininal Lfft cfArchibaldo": "Criminal Life of Archibaldo",
    "Charm cf tile Bourgeoisie": "Charm of the Bourgeoisie",
    "Ol!Ject ojDesire": "Object of Desire",
    "tromper rlEiɫ": "tromper l'oeil",
    "trompe ['CEil": "trompe l'oeil",
    "plato": "Plato",
    "ip. the name": "in the name",
    "precedil18": "preceding",
    "oft/ze big Other": "of the big Other",
    "overlook)ng": "overlooking",
    "evel)lthing": "everything",
    "p!JIchotic": "psychotic",
    "Threepen'!J' Opera": "Threepenny Opera",
    "sl!Jet d'enonaation": "sujet d'énonciation",
    "sl!Jet d'enonce": "sujet d'énoncé",
    "szget d'enonce": "sujet d'énoncé",
    "sujet d'enonciation": "sujet d'énonciation",
    "'!Jnthesis'is exactfy thesame": "'synthesis' is exactly the same",
    "ve!J'definitioTL": "very definition",
    "butfor all that,you": "but for all that, you",
    "reallY hurtmefIn": "really hurt me! In",
    "nzelotfy": "melody",
    "recondliation": "reconciliation",
    "level ofform": "level of form",
    "Su£?ject as an 'al15wer of the Real'": "Subject as an 'answer of the Real'",
    "al15Wer": "answer",
    "al15wer": "answer",
    "oiject in suijea": "object in subject",
    "suiject": "subject",
    "oijective": "objective",
    "objectivication": "objectification",
    "basiૣ": "basis",
    "Thing in-itself": "Thing-in-itself",
    "barting": "barring",
    "barouraccess": "bar our access",
    "itselfhindered": "itself hindered",
    "ac10se": "a close",
    "Kern unseres Wesens": "Kern unseres Wesens",
    "of the subject before subjectivation": "of the subject before subjectivation",
    "ifI": "if I",
    "Freud' s": "Freud's",
    "subjea presumed": "subject presumed",
    "subject presumed to ergo": "subject presumed to enjoy",
    "irifillitum": "infinitum",
    "1930S": "1930s",
    "consequૡnces": "consequences",
    "ScheUingian": "Schellingian",
    "positivi9'": "positivity",
    "negativi9'": "negativity",
    "nothil18": "nothing",
    "series offailures": "series of failures",
    "positivefunction": "positive function",
    "incompatibili9'": "incompatibility",
    "determinations ofSociety": "determinations of Society",
    "Thing-in-itself 0/ the": "Thing-in-itself of the",
    "access to it The": "access to it. The",
    "w1!Y": "Why",
    "obsceni9'": "obscenity",
    "Qy.estioning": "Questioning",
    "enCOU1lters": "encounters",
    "of'mere appearance'": "of 'mere appearance'",
    "10tl'The": "lot.' The",
    "the birds are &lt;1&gt;": "the birds are Φ",
    "the birds are <1>": "the birds are Φ",
    "5(૦)": "S(Ⱥ)",
    "itse!fas": "itself as",
    "s'insaireJ": "s'inscrire]",
    "Very well, 1 shall not": "Very well, I shall not",
    "impotent You": "impotent. You",
    "pla.ce": "place",
    "ofsublimi9J": "of sublimity",
    "philosophy ofReliaion": "Philosophy of Religion",
    "Erhabenheiɬ": "Erhabenheit]",
    "VerstandJ": "Verstand]",
    "Yovel' s": "Yovel's",
    "Yo vel' s": "Yovel's",
    "inrroduces": "introduces",
    "of'external": "of 'external",
    "hirnself": "himself",
    "fgure": "figure",
    "ctucial": "crucial",
    "CritiqueofJudgement": "Critique of Judgement",
    "VGutSsanceJ": "[jouissance]",
    "byond": "beyond",
    "ifideas": "of ideas",
    "EthicofP!Jchoanafysis": "Ethic of Psychoanalysis",
    "greamess": "greatness",
    "Azifheburwl": "Aufhebung]",
    "Fliissigwerden": "Flüssigwerden",
    "Kant himseff": "Kant himself",
    "stil remains": "still remains",
    "field 0/ representation": "field of representation",
    "Idea itselJas": "Idea itself as",
    "Thing-in-itselJ": "Thing-in-itself",
    "inadequa9'": "inadequacy",
    "if the appearance": "of the appearance",
    "physiognomy and Phrenolog;y": "Physiognomy and Phrenology",
    "change oflevel": "change of level",
    "realiry": "reality",
    "body ot ifyou like": "body or if you like",
    "M!sone": "maison",
    "ifthe signifier": "of the signifier",
    "signi.fier": "signifier",
    "offlatte1)": "of flattery",
    "if silent": "of silent",
    "if Ilatte,y": "of flattery",
    "ro Wealth": "to Wealth",
    "ofh ypocritical": "of hypocritical",
    "th ey are": "they are",
    "ullheard-ifsense": "unheard-of sense",
    "stalinist phenomenonɪ": "Stalinist phenomenon.",
    "Wealth is the Self": "Wealth is the Self",
    "encoll·nter": "encounter",
    "Positi11g, external, determinate riflection": "Positing, External, Determinate Reflection",
    "texl": "text",
    "oftenvards": "afterwards",
    "delqy": "delay",
    "Thina-in-itseffis": "Thing-in-itself is",
    "t1zrol18h": "through",
    "signi!Jing": "signifying",
    "existence itsel£": "existence itself",
    "itselflikeable": "itself likeable",
    "narcis sistic": "narcissistic",
    "undennining": "undermining",
    "formallY": "formally",
    "responsible-guil9'": "responsible-guilty",
    "positiveempirical": "positive-empirical",
    "awqy": "away",
    "aheap": "a heap",
    "ofpositi118": "of positing",
    "presupposi118": "presupposing",
    "positi118": "positing",
    "categOlY": "category",
    "exemplifJ": "exemplify",
    "Just an [ideological]": "just an 'ideological",
    "[ideological] appearance'": "ideological appearance'",
    "surpassing the external": "surpassing the external",
    "reflectioninto-itself": "reflection-into-itself",
    "0/ the act": "of the act",
    "alreacfy": "already",
    "prisoner 0/ the field": "prisoner of the field",
    "notlli118": "nothing",
    "Histo!), if the Communist Pa'9'": "History of the Communist Party",
    "responsibili9'": "responsibility",
    "reali9'": "reality",
    "W'9' substance becomes suEved": "way substance becomes subject",
    "alw'9's": "always",
    "Presupposi118 the positing": "Presupposing the Positing",
    "an 0 bjectivation": "an objectivation",
    "theJorm 0/": "the form of",
    "extemali9'": "externality",
    "qfsomethina objectivefy": "of something objectively",
    "itseifin": "itself in",
    "saa!fice": "sacrifice",
    "itse!f!'": "itself!'",
    "evelJlthin,g": "everything",
    "iese!f": "itself",
    "suEved": "subject",
    "selfflSsure": "self-fissure",
    "precisefy ill so Jar": "precisely in so far",
    "expen\"ences": "experiences",
    "appearas": "appear as",
    "subjectMonarch": "subject-Monarch",
}


FOOTNOTE_TARGETS = {
    1: "constituent of reality",
    2: "words from which belief has gone",
    3: "them and so sharpens them",
    4: "simple determinations of thought",
    5: "I can make it homogeneous with myself",
    6: "system 'is the belly turned mind'",
    7: "embraces and holds everything within itself",
    8: "pushes it away from itself, and thus liberates it",
    9: "nature itself sublates its externality",
    10: "frees from a certain type of attachment",
    11: "moment of its particularity",
    12: "is the totality in this form - nature",
    13: "without the moment of subjectivity",
    14: "standard deconstructionist notion of undecidability",
}


def clean_line_join(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    output = ""
    for line in lines:
        if not line:
            output += "\n\n"
            continue
        if output.endswith(("-", "\u00ad")):
            output = output[:-1] + line
            continue
        if output and not output.endswith(("\n", " ")):
            output += " "
        output += line
    output = output.replace("\u00ad", "")
    output = re.sub(r"\s+", " ", output).strip()
    return output


def clean_text(text: str) -> str:
    text = clean_line_join(text)
    text = text.replace("\u082f", "l")
    text = text.replace("\u083f", "l")
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = text.replace(" . . .", " ...")
    text = text.replace(" ' ", " '")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ref(num: int) -> str:
    return f'<sup id="fnref-{num}"><a href="#fn-{num}">{num}</a></sup>'


def footnote_popover(num: int, notes: dict[int, str] | None = None, prefix: str = "") -> str:
    notes = notes or FOOTNOTES
    note = html.escape(notes[num], quote=False)
    note_id = f"{prefix}{num}" if prefix else str(num)
    return (
        f'<span class="footnote-popover">'
        f'<sup id="fnref-{note_id}" class="note-ref"><a href="#fn-{note_id}">{num}</a></sup>'
        f'<span class="floating-note" id="sn-{note_id}" role="note">'
        f'<span class="floating-note-number">{num}</span> {note}</span>'
        f'</span>'
    )


def ensure_figure_assets(doc: fitz.Document) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for figure in FIGURES.values():
        page = doc[figure["page"]]
        image = page.get_images(full=True)[figure["index"]]
        pix = fitz.Pixmap(doc, image[0])
        if pix.n > 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        pix.save(FIGURE_DIR / figure["filename"])


def figure_html(slug: str) -> str:
    figure = FIGURES[slug]
    src = image_file_to_data_uri(FIGURE_DIR / figure["filename"])
    return (
        '<figure class="book-figure">'
        f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(figure["alt"], quote=True)}">'
        f'<figcaption>{html.escape(figure["caption"], quote=False)}</figcaption>'
        '</figure>'
    )


def insert_footnotes(text: str) -> str:
    for num, target in FOOTNOTE_TARGETS.items():
        marker = ref(num)
        if marker in text:
            continue
        idx = text.find(target)
        if idx == -1:
            raise RuntimeError(f"Could not locate footnote target {num}: {target}")
        end = idx + len(target)
        while end < len(text) and text[end] in ".',;:)":
            end += 1
        text = text[:end] + marker + text[end:]
    text = text.replace("reality).'<sup", "reality).<sup")
    text = text.replace("gone.<sup", "gone.'<sup")
    text = text.replace("</sup>\" As", "</sup> As")
    text = text.replace("<sup id=\"fnref-4\"><a href=\"#fn-4\">4</a></sup>4", "<sup id=\"fnref-4\"><a href=\"#fn-4\">4</a></sup>")
    text = text.replace("<sup id=\"fnref-5\"><a href=\"#fn-5\">5</a></sup>5", "<sup id=\"fnref-5\"><a href=\"#fn-5\">5</a></sup>")
    text = text.replace("<sup id=\"fnref-6\"><a href=\"#fn-6\">6</a></sup>6", "<sup id=\"fnref-6\"><a href=\"#fn-6\">6</a></sup>")
    text = text.replace("<sup id=\"fnref-8\"><a href=\"#fn-8\">8</a></sup>8", "<sup id=\"fnref-8\"><a href=\"#fn-8\">8</a></sup>")
    text = text.replace("<sup id=\"fnref-9\"><a href=\"#fn-9\">9</a></sup>9", "<sup id=\"fnref-9\"><a href=\"#fn-9\">9</a></sup>")
    text = text.replace("<sup id=\"fnref-10\"><a href=\"#fn-10\">10</a></sup> '0", "<sup id=\"fnref-10\"><a href=\"#fn-10\">10</a></sup>")
    text = text.replace("<sup id=\"fnref-11\"><a href=\"#fn-11\">11</a></sup>n", "<sup id=\"fnref-11\"><a href=\"#fn-11\">11</a></sup>")
    text = text.replace("undecidability.'<sup id=\"fnref-14\"><a href=\"#fn-14\">14</a></sup>4", "undecidability.<sup id=\"fnref-14\"><a href=\"#fn-14\">14</a></sup>")
    text = text.replace("medium of, grey'", "medium of 'grey'")
    text = text.replace("Möglichkeit getilgte Wirklichkeit, its", "Möglichkeit getilgte Wirklichkeit], its")
    text = text.replace("inner potential When", "inner potential. When")
    text = text.replace("Hegel writes, If", "Hegel writes: If")
    text = text.replace("sublating itself So,", "sublating itself. So,")
    text = text.replace("The Idea' decides'", "the Idea 'decides'")
    text = text.replace("the Idea' decides'", "the Idea 'decides'")
    text = text.replace("itself The passage", "itself. The passage")
    text = text.replace("to take away'] Speculative", "to take away']. Speculative")
    text = text.replace("it includes itself-", "it includes itself -")
    text = text.replace("met(and", "met (and")
    text = text.replace("Things. 'materially exist'", "Things 'materially exist'")
    text = text.replace("myself<sup id=\"fnref-5\"", "myself.<sup id=\"fnref-5\"")
    text = text.replace("liberates it.<sup id=\"fnref-8\"", "liberates it.'<sup id=\"fnref-8\"")
    text = text.replace("form - nature<sup id=\"fnref-12\"", "form - nature.<sup id=\"fnref-12\"")
    text = text.replace("subjectivity<sup id=\"fnref-13\"", "subjectivity.<sup id=\"fnref-13\"")
    text = text.replace("them.)", "them.")
    text = text.replace("itself.8", "itself.")
    text = text.replace("undecidability.'4", "undecidability.")
    return text


def html_paragraph(text: str, klass: str | None = None) -> str:
    attr = f' class="{klass}"' if klass else ""
    return f"<p{attr}>{html.escape(text, quote=False)}</p>"


def escape_with_inline_html(text: str) -> str:
    placeholders: dict[str, str] = {}

    def stash(match: re.Match[str]) -> str:
        key = f"@@INLINE{len(placeholders)}@@"
        placeholders[key] = match.group(0)
        return key

    text = re.sub(r'<span class="footnote-popover">.*?</span></span>', stash, text)
    escaped = html.escape(text, quote=False)
    for key, value in placeholders.items():
        escaped = escaped.replace(key, value)
    return escaped


def extract_preface(doc: fitz.Document) -> list[str]:
    paragraphs: list[str] = []
    for pno in range(5, 21):
        page = doc[pno]
        blocks = sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))
        for block in blocks:
            x0, y0, _x1, _y1, text = block[:5]
            footnote_top = 450 if pno == 5 else 520
            if y0 > footnote_top:
                continue
            if pno > 5 and y0 < 55:
                continue
            if pno == 5 and y0 < 90:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)(preface|[ivxlcdm]+|\d+)\s*", cleaned):
                continue
            paragraphs.append(cleaned)
    body = " ".join(paragraphs)
    body = insert_footnotes(body)
    # Split at natural paragraph starts recovered from the page text.
    starters = [
        "Two examples",
        "The question is then",
        "However, as Lacan taught us",
        "Let us take",
        "The problem with Understanding",
        "Back in the 1960s",
        "The same mortification",
        "This 'simplification'",
        "The dialectical approach",
        "Hegel's formulation",
        "Once we grasp",
        "Is what he offers",
        "In this strict sense",
        "Does then",
        "The same move is accomplished",
        "The way abrogation",
        "True cognition",
        "So, what about",
        "This is why Hegelian cognition",
        "For Hegel, on the contrary",
        "'Absolute freedom'",
        "This is how one should read",
        "But this determination",
        "One should here reread",
        "The passage from Kant",
        "On a first approach",
        "This brings us",
        "Along the same lines",
        "With regard to material reality",
        "When Alain Badiou",
        "Back to our main line",
        "So, to pursue",
        "What this means is",
        "Perhaps what",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def extract_introduction(doc: fitz.Document) -> list[str]:
    blocks: list[str] = []
    for pno in range(21, 30):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 520:
                continue
            if pno == 21 and y0 < 70:
                continue
            if pno > 21 and y0 < 55:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)(introduction|[ivxlcdm]+|\d+|the sublime object of ideology)\s*", cleaned):
                continue
            if cleaned.startswith("•"):
                blocks.append("\n\n" + cleaned)
            else:
                blocks.append(cleaned)

    body = " ".join(blocks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)
    body = body.replace("universe).'", f"universe).{footnote_popover(1, INTRO_FOOTNOTES, 'intro-')}")
    body = body.replace(
        "Althusser's theory, a traumatic kernel",
        f"Althusser's theory{footnote_popover(2, INTRO_FOOTNOTES, 'intro-')}, a traumatic kernel",
    )
    body = body.replace("proletarian'.J", f"proletarian'.{footnote_popover(3, INTRO_FOOTNOTES, 'intro-')}")
    body = body.replace("structure}.4", f"structure).{footnote_popover(4, INTRO_FOOTNOTES, 'intro-')}")

    starters = [
        "The answer to this enigma",
        "Why, then",
        "With Habermas",
        "With Foucault",
        "It is not very difficult",
        "Although Althusser",
        "In this perspective",
        "In contrast to this",
        "Marxist notion",
        "This traditional notion",
        "It is upon the unity",
        "The basic feature",
        "Psychoanalytic 'essentialism'",
        "That is to say",
        "All 'culture'",
        "We have the same logic",
        "It is the merit",
        "Every attempt",
        "Here we can see",
        "What would be",
        "The answer",
        "It is in this precise sense",
        "The critique",
        "The aim of this book",
        "It is my belief",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = body.replace(" • ", "\n\n• ")
    body = body.replace("traditional\n\nMarxist notion", "traditional Marxist notion")
    body = body.replace("the\n\nMarxist notion", "the Marxist notion")
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_one_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_ONE_FOOTNOTES, "ch1-")
    replacements = [
        ("troubling Freud day and night).'", f"troubling Freud day and night).{fn(1)}"),
        ("has been transferred on to it'!", f"has been transferred on to it'{fn(2)}"),
        ("concealed subject matter'.J", f"concealed subject matter'.{fn(3)}"),
        ("explanation of its peculiar nature.4", f"explanation of its peculiar nature.{fn(4)}"),
        ("that determination takes place.5", f"that determination takes place.{fn(5)}"),
        ("from this form itself'.6", f"from this form itself'.{fn(6)}"),
        ("the value of the product.7", f"the value of the product.{fn(7)}"),
        ("came into existence with it.8", f"came into existence with it.{fn(8)}"),
        ("any matter found in nature'.9", f"any matter found in nature'.{fn(9)}"),
        ("carrier of its social function.'O", f"carrier of its social function.{fn(10)}"),
        ("what they think and say about it'.\"", f"what they think and say about it'.{fn(11)}"),
        ("abstraction would not arise.ll", f"abstraction would not arise.{fn(12)}"),
        ("what we call the feudal times.\" J", f"what we call the feudal times.{fn(13)}"),
        ("fantastic form of a relation between things'.'4", f"fantastic form of a relation between things'.{fn(14)}"),
        ("the type of the genus homo.'5", f"the type of the genus homo.{fn(15)}"),
        ("because he is king.'6", f"because he is king.{fn(16)}"),
        ("in a Hegelian sense;'7", f"in a Hegelian sense;{fn(17)}"),
        ("between the products of labour.'8", f"between the products of labour.{fn(18)}"),
        ("under her clothes, she is totally naked'.'9", f"under her clothes, she is totally naked'.{fn(19)}"),
        ("the interconnection becomes mystical.20", f"the interconnection becomes mystical.{fn(20)}"),
        ("the Chorus will do so in your place'.\"", f"the Chorus will do so in your place'.{fn(21)}"),
        ("leads the mind unconsciously along with it.22", f"leads the mind unconsciously along with it.{fn(22)}"),
        ("first principle destroys it. '3", f"first principle destroys it.{fn(23)}"),
        ("authority, without truth).'4", f"authority, without truth).{fn(24)}"),
        ("universal principle.'25", f"universal principle.{fn(25)}"),
        ("you have paid nothing.'26", f"you have paid nothing.{fn(26)}"),
        ("Pascalian 'machine';27", f"Pascalian 'machine';{fn(27)}"),
        ("fallen on them.>s", f"fallen on them.{fn(28)}"),
        ("the Real of our desire!9", f"the Real of our desire.{fn(29)}"),
        ("The Four Fundamental Concepts of Psycho-Analysis.l°", f"The Four Fundamental Concepts of Psycho-Analysis.{fn(30)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 1 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_one(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(33, 86):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 540:
                continue
            if pno > 33 and y0 < 55:
                continue
            if pno == 33 and y0 < 130:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)(how did marx invent the symptom\??|[ivxlcdm]+|\d+|the sublime object of ideology|how did marx invent the symptom!?|\d+ the sublime object of ideology)\s*", cleaned):
                continue
            if re.match(r"^\d{1,2}\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)

    body = insert_chapter_one_footnotes(body)
    body = re.sub(
        r"how 29 Jacques Lacan, The Four .*? 30 Ibid\., Chapter 6\. does he know",
        "how does he know",
        body,
    )

    headings = [
        ("Marx, Freud: the analysis of form", "Marx, Freud: The Analysis of Form"),
        ("The unconscious of the commodity-form", "The Unconscious of the Commodity-Form"),
        ("The form of thought", "The Form of Thought"),
        ("The social symptom", "The Social Symptom"),
        ("Commodity fetishism", "Commodity Fetishism"),
        ("Totalitarian laughter", "Totalitarian Laughter"),
        ("cynicism as a form of ideology", "Cynicism as a Form of Ideology"),
        ("Ideological fantasy", "Ideological Fantasy"),
        ("The objectivity of belief", "The Objectivity of Belief"),
        ("'Law is Law'", "'Law is Law'"),
        ("Kafka, critic of Althusser", "Kafka, Critic of Althusser"),
        ("Fantasy as a support of reality", "Fantasy as a Support of Reality"),
        ("Surplus-value and surplus-enjoyment", "Surplus-Value and Surplus-Enjoyment"),
    ]
    for raw, title in headings:
        body = body.replace(raw, f"\n\n@@h3:{title}\n\n", 1)

    starters = [
        "According to Lacan",
        "The notorious reproach",
        "This kind of reproach",
        "Herein, then",
        "It is this unconscious",
        "As is often",
        "I used at one time",
        "At bottom",
        "Freud proceeds here",
        "The crucial thing",
        "We must, then",
        "Why did the Marxian",
        "The theoretician",
        "Herein lies",
        "After a series",
        "The exchange of commodities",
        "As Sohn-Rethel pointed out",
        "How tempting",
        "Here we have touched",
        "A coin has it stamped",
        "If, then",
        "Here we have one",
        "The symbolic order",
        "We are now able",
        "This does not mean",
        "During the act",
        "Such a misrecognition",
        "Thus, in speaking",
        "This misrecognition brings",
        "The crucial paradox",
        "This is probably",
        "How, then",
        "Marx 'invented",
        "This symptom emerges",
        "The 'quantitative'",
        "And in the Marxian",
        "This is also",
        "In his attribution",
        "To grasp",
        "In a first approach",
        "Consequently",
        "Such a misrecognition",
        "The commodity A",
        "In a sort",
        "This short note",
        "Marx pursues",
        "Such expressions",
        "'Being-a-king'",
        "How can one",
        "What we have here",
        "The two forms",
        "This fetishism",
        "The retreat",
        "This is why",
        "With the establishment",
        "The universal freedom",
        "The fundamental level",
        "Already in the 1950s",
        "As in the old",
        "The point is",
        "But all this",
        "Our question is",
        "The formula",
        "It is no longer",
        "The cynical subject",
        "It is this cynical",
        "Such a cynical stance",
        "Here we must distinguish",
        "The crucial point",
        "If the illusion",
        "This illusion",
        "So now",
        "What they overlook",
        "Ideological fantasy",
        "According to the well-known",
        "The social reality",
        "From this standpoint",
        "The problem",
        "We can now",
        "The externality",
        "The beauty of it",
        "This is how",
        "Even if we",
        "In so-called primitive",
        "But to avoid",
        "There are some",
        "We all know",
        "In contrast",
        "What we call",
        "As soon as",
        "This was already",
        "According to Pascal",
        "Here Pascal",
        "It follows",
        "Custom is",
        "The only real obedience",
        "Even more than",
        "Certainly we must",
        "'External' obedience",
        "This is the fundamental",
        "But for the Law",
        "It would therefore",
        "It is highly significant",
        "What is 'repressed'",
        "The necessary structural",
        "In other words",
        "The crucial text",
        "Far from being",
        "The Marxist who participates",
        "The external ritual",
        "This is what",
        "An interesting case",
        "The film is worth",
        "The only door",
        "When we subject",
        "Belief is",
        "It is this short-circuit",
        "But the weak point",
        "In this respect",
        "And again",
        "All the 'secrets'",
        "The point is rather",
        "This is the dimension",
        "What does it mean",
        "A father had",
        "The usual interpretation",
        "The Lacanian reading",
        "We can rephrase",
        "It is exactly",
        "To explain this logic",
        "Here Lacan",
        "After awakening",
        "This, however",
        "The Lacanian thesis",
        "Let us examine",
        "Let us suppose",
        "At first sight",
        "Herein lies",
        "It is the same",
        "In the usual",
        "We have only",
        "This formula",
        "All we have",
        "And here",
        "How can we",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = body.replace(" • ", "\n\n• ")
    body = body.replace(" . obstinacy", " obstinacy")
    body = body.replace("equalobstinacy", "equal obstinacy")
    body = body.replace(".: Thus", ". Thus")
    body = body.replace("this reality would dissolve itself\n\nThis is probably", "this reality would dissolve itself.\n\nThis is probably")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_two_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_TWO_FOOTNOTES, "ch2-")
    replacements = [
        ("until we have realized its meaning.'", f"until we have realized its meaning.{fn(1)}"),
        ("will have been',>", f"will have been'.{fn(2)}"),
        ("included in the account'.J", f"included in the account'.{fn(3)}"),
        ("only he did not know it.4", f"only he did not know it.{fn(4)}"),
        ("contingent character.;", f"contingent character.{fn(5)}"),
        ("I am now going to shut it.'6", f"I am now going to shut it.{fn(6)}"),
        ("Free will and predestination in one sentence and both true.7", f"Free will and predestination in one sentence and both true.{fn(7)}"),
        ("White Star Line called its ship the Titanic", f"White Star Line called its ship the Titanic.{fn(8)}"),
        ("Saint Thomas, the saint...).9", f"Saint Thomas, the saint...).{fn(9)}"),
        ("this blossom in his side was destroying him\"", f"this blossom in his side was destroying him\"{fn(10)}"),
        ("destroying him.ll", f"destroying him.{fn(11)}"),
        ("'Kant avec Sade'.1Z", f"'Kant avec Sade'.{fn(12)}"),
        ("middle of a forest. I)", f"middle of a forest.{fn(13)}"),
        ("beyond their own personal development. '4", f"beyond their own personal development.{fn(14)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 2 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_two(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(87, 123):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            page_bottom = 575 if pno == 104 else 540
            if y0 >= page_bottom:
                continue
            if pno > 87 and y0 < 55:
                continue
            if pno == 87 and y0 < 115:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)(from symptom to sinthome|the sublime object of ideology|\d+|\d+ from symptom to sinthome|lack in the other)\s*", cleaned):
                continue
            if re.match(r"^\d{1,2}\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)

    body = insert_chapter_two_footnotes(body)
    body = body.replace("the Republic would regain its full splendour. But", "the Republic would regain its full splendour. But")
    body = body.replace("this educational effect is spoilt It", "this educational effect is spoilt. It")

    headings = [
        ("The Dialectics of the Symptom", "The Dialectics of the Symptom", "h3"),
        ("Back to the future", "Back to the Future", "h4"),
        ("Repetition in History", "Repetition in History", "h4"),
        ("Hegel with Austen", "Hegel with Austen", "h4"),
        ("A time trap", "A Time Trap", "h4"),
        ("Symptom as Real", "Symptom as Real", "h3"),
        ("The 'Titanic as Symptom", "The 'Titanic' as Symptom", "h4"),
        ("Return to the future", "Return to the Future", "h4"),
        ("There is no metalanguage", "There Is No Metalanguage", "h4"),
        ("Symptom as sinthome", "Symptom as Sinthome", "h4"),
        ("In you more than yourself", "'In You More Than Yourself'", "h4"),
        ("Ideological jouissance", "Ideological Jouissance", "h4"),
    ]
    for raw, title, level in headings:
        body = body.replace(raw, f"\n\n@@{level}:{title}\n\n", 1)
    starters = [
        "The only reference",
        "Wiener posits",
        "The analysis",
        "The Lacanian answer",
        "Symptoms are",
        "As soon as",
        "Thus, 'things",
        "This knowledge",
        "If - as Lacan",
        "Transference is",
        "If this paradoxical",
        "A distinguished",
        "When he encounters",
        "The only action",
        "This, therefore",
        "The initial",
        "This introduces",
        "We find the same",
        "The time structure",
        "The transference",
        "We find the same logic",
        "We are alluding",
        "If we merely",
        "If we look",
        "This is also",
        "Why this need",
        "Hegel developed",
        "To the 'opinion'",
        "The Truth thus",
        "The whole problem",
        "What is the reason",
        "At first sight",
        "But such an idea",
        "The crucial point",
        "It is not only",
        "In other words",
        "Hegel was thus",
        "The fact that",
        "Austen, not Austin",
        "In Pride and Prejudice",
        "It is no wonder",
        "This double failure",
        "Only after they",
        "At the end",
        "Here we encounter",
        "This logic of",
        "Robert Heinlein's",
        "Here we have",
        "If, during",
        "The oversight",
        "This is perhaps",
        "The knowledge",
        "In a homologous way",
        "The first association",
        "This somehow",
        "Fourteen years later",
        "On April 10",
        "Robertson called",
        "The reasons",
        "New dangers",
        "And if there",
        "This somehow",
        "At this point",
        "Lacan's answer",
        "To seize",
        "When Lacan introduced",
        "However, in the last",
        "Symptom as real",
        "We can use",
        "At the beginning",
        "The symptom arises",
        "In other words",
        "But here",
        "The Lacanian answer",
        "In locating",
        "In this way",
        "Lacan tried",
        "What we must",
        "If the symptom",
        "That is why",
        "This, then",
        "Now it is",
        "So if woman",
        "In so far",
        "Is not Franz",
        "In his right side",
        "At first sight",
        "The wound is",
        "Syberberg's inversion",
        "The first",
        "But there is",
        "This is the paradox",
        "To take",
        "From this perspective",
        "With the designation",
        "The text",
        "The Lacanian criticism",
        "So we can",
        "This is why",
        "But in what",
        "Not in some",
        "The moral Law",
        "Of course",
        "Let us take",
        "This surplus",
        "And Fascism",
        "The ideological power",
        "This is the hidden",
        "In this passage",
        "Here we could",
        "From a whole series",
        "In other words",
        "It is the same",
        "But the point",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_three_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_THREE_FOOTNOTES, "ch3-")
    replacements = [
        ("description proves false. I", f"description proves false.{fn(1)}"),
        ("it is not gold!", f"it is not gold!{fn(2)}"),
        ("there were unicorns.)", f"there were unicorns.){fn(3)}"),
        ("causal chain of communication theory.4", f"causal chain of communication theory.{fn(4)}"),
        ("what others are using it to refer to'5", f"what others are using it to refer to'{fn(5)}"),
        ("referring to that hermit.6", f"referring to that hermit.{fn(6)}"),
        ("Lacanian graph of desire?", f"Lacanian graph of desire.{fn(7)}"),
        ("S OD*),s", f"S OD*),{fn(8)}"),
        ("level at which we fix it.", f"level at which we fix it.{fn(9)}"),
        ("[king, master, wife... J?'10", f"[king, master, wife... ]?'{fn(10)}"),
        ("nailed to the cross.\"", f"nailed to the cross.{fn(11)}"),
        ("process of knowledge. 12", f"process of knowledge.{fn(12)}"),
        ("paranoid construction of the 'Jew'.ll", f"paranoid construction of the 'Jew'.{fn(13)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 3 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_three(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(125, 175):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 540:
                continue
            if pno > 125 and y0 < 55:
                continue
            if pno == 125 and y0 < 115:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)('che vuoi\\?'|the sublime object of ideology|\\d+|\\d+ the sublime object of ideology|you only die twice)\s*", cleaned):
                continue
            if re.match(r"^\d{1,2}\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)
    body = insert_chapter_three_footnotes(body)
    body = body.replace("The Jew and Antigone We come across", "The Jew and Antigone\n\nWe come across")

    headings = [
        ("Identity", "Identity", "h3"),
        ("The ideological quilt'", "The Ideological Quilt", "h4"),
        ("Descriptivism versus antidescriptivism", "Descriptivism versus Antidescriptivism", "h4"),
        ("The two myths", "The Two Myths", "h4"),
        ("Rigid designator and objet a", "Rigid Designator and Objet a", "h4"),
        ("The ideological anamorphosis", "The Ideological Anamorphosis", "h4"),
        ("Identification (Lower Level of the Graph of Desire)", "Identification (Lower Level of the Graph of Desire)", "h3"),
        ("Retroactivity of Meaning", "Retroactivity of Meaning", "h4"),
        ("Graph I", "Graph I", "h4"),
        ("The 'effect of retroversion'", "The 'Effect of Retroversion'", "h4"),
        ("Graph ll", "Graph II", "h4"),
        ("Image and gaze", "Image and Gaze", "h4"),
        ("Beyond Identification (Upper Level of the Graph of Desire)", "Beyond Identification (Upper Level of the Graph of Desire)", "h3"),
        ("'Che vuoi?'", "'Che Vuoi?'", "h4"),
        ("Graph ID", "Graph III", "h4"),
        ("The Jew and Antigone", "The Jew and Antigone", "h4"),
        ("Fantasy as a screen for the desire of the Other", "Fantasy as a Screen for the Desire of the Other", "h4"),
        ("The inconsistent Other of Jouissance", "The Inconsistent Other of Jouissance", "h4"),
        ("Completed Graph", "Completed Graph", "h4"),
        ("Going through' the social fantasy", "'Going Through' the Social Fantasy", "h4"),
    ]
    for raw, title, level in headings:
        body = body.replace(raw, f"\n\n@@{level}:{title}\n\n", 1)
    for title, slug in [
        ("Graph I", "graph-i"),
        ("Graph II", "graph-ii"),
        ("Graph III", "graph-iii"),
        ("Completed Graph", "completed-graph"),
    ]:
        body = body.replace(f"@@h4:{title}\n\n", f"@@h4:{title}\n\n@@figure:{slug}\n\n", 1)

    starters = [
        "What creates",
        "The multitude",
        "This, perhaps",
        "The point de capiton",
        "Let us take",
        "In the ideological space",
        "Descriptivists",
        "The antidescriptivist",
        "The same also applies",
        "In other words",
        "What is at stake",
        "Bearing in mind",
        "The proof",
        "To refute",
        "Imagine that",
        "What Searle",
        "The ironic part",
        "If, consequently",
        "Donnellan has",
        "Suppose that",
        "Today, the original",
        "Why is this",
        "The basic problem",
        "What is overlooked",
        "It is the name",
        "It is not",
        "The anti-Semitic",
        "Now, having",
        "The answer",
        "Lacan articulated",
        "For example",
        "Let us then begin",
        "What we have",
        "The point de capiton",
        "A crucial feature",
        "To grasp",
        "Already, at",
        "This therefore",
        "One can see",
        "We have already",
        "This interplay",
        "The only problem",
        "After every",
        "This question",
        "The Lacanian answer",
        "This is why",
        "The Other is",
        "The subject",
        "Perhaps the strongest",
        "How does Mary",
        "The painting",
        "Martin Scorsese",
        "We come across",
        "The conclusion",
        "The paradox",
        "Fantasy appears",
        "The usual definition",
        "By entering",
        "Let us take Hitchcock",
        "How does she",
        "This is also",
        "What we must add",
        "This is why",
        "Here we encounter",
        "We can now",
        "If we look",
        "In this way",
        "We can also",
        "Jews are clearly",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_four_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_FOUR_FOOTNOTES, "ch4-")
    replacements = [
        ("sublime body. Today", f"sublime body.{fn(1)} Today"),
        ("keep out of sight.2", f"keep out of sight.{fn(2)}"),
        ("portions of its content'.J", f"portions of its content'.{fn(3)}"),
        ("same value as the old speech.4", f"same value as the old speech.{fn(4)}"),
        ("decipher completely.'5", f"decipher completely.'{fn(5)}"),
        ("will have been.6", f"will have been.{fn(6)}"),
        ("hypothesis of domination'7", f"hypothesis of domination'{fn(7)}"),
        ("personifying the State.8", f"personifying the State.{fn(8)}"),
        ("an empty place.9", f"an empty place.{fn(9)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 4 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_four(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(175, 199):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 540:
                continue
            if pno > 175 and y0 < 55:
                continue
            if pno == 175 and y0 < 130:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(r"(?i)(you only die twice|the sublime object of ideology|\d+|\d+ the sublime object of ideology|the subject)\s*", cleaned):
                continue
            if re.match(r"^\d{1,2}\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)
    body = insert_chapter_four_footnotes(body)

    headings = [
        ("Between the two deaths", "Between the Two Deaths", "h3"),
        ("Revolution as repetition", "Revolution as Repetition", "h4"),
        ("The 'perspective of the Last Judgement'", "The 'Perspective of the Last Judgement'", "h4"),
        ("From the Master to the Leader", "From the Master to the Leader", "h4"),
    ]
    for raw, title, level in headings:
        body = body.replace(raw, f"\n\n@@{level}:{title}\n\n", 1)

    starters = [
        "The connection",
        "In the first period",
        "In the second period",
        "In the third period",
        "The symbolic order",
        "This distinction",
        "In the first period",
        "In the second period",
        "In the third period",
        "The Freudian",
        "The stimulus",
        "This difference",
        "Today, we can",
        "Consider Tom",
        "Or take",
        "Lacan conceives",
        "In the whole",
        "These Theses",
        "That is to say",
        "Historical materialism",
        "The story",
        "What strikes",
        "But let us",
        "We cannot",
        "What Benjamin",
        "This refusal",
        "Eingedenken certainly",
        "We would none",
        "By confining",
        "A historical materialist",
        "Thinking involves",
        "Here we have",
        "It is this",
        "The past itself",
        "Repetition is",
        "The monad",
        "So, contrary",
        "Apropos",
        "At this precise",
        "Actual history",
        "Let us recall",
        "This is the idealism",
        "We can thus",
        "From the point",
        "The difference",
        "The Stalinist",
        "Where, then",
        "The transubstantiated",
        "And this fact",
        "The totalitarian Leader",
        "That is why",
        "The Lacanian definition",
        "In a democratic order",
        "Because the People",
        "It is against",
        "Lefort interprets",
        "At the moment",
        "Only the acceptance",
        "So-called",
        "In short",
        "Here Hegel",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = body.replace(" • ", "\n\n• ")
    body = body.replace(" •\n\n", "\n\n• ")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_five_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_FIVE_FOOTNOTES, "ch5-")
    replacements = [
        ("discursive articulation.' In contrast", f"discursive articulation.'{fn(1)} In contrast"),
        ("as its signifier! Even at", f"as its signifier!{fn(2)} Even at"),
        ("You cannot hurt me with it.') In this way", f"You cannot hurt me with it.'){fn(3)} In this way"),
        ("cannot do anything.4", f"cannot do anything.{fn(4)}"),
        ("miss its address.5", f"miss its address.{fn(5)}"),
        ("symbolic universe of the subject, but in the 1970s", f"symbolic universe of the subject,{fn(6)} but in the 1970s"),
        ("Critique of Practical Reason.7", f"Critique of Practical Reason.{fn(7)}"),
        ("life before this [terrestrial] life.8", f"life before this [terrestrial] life.{fn(8)}"),
        ("deadlock offormalization',9", f"deadlock of formalization',{fn(9)}"),
        ("status of free association.'o", f"status of free association.{fn(10)}"),
        ("society.\" Adorno", f"society.{fn(11)} Adorno"),
        ("in the mistake'.\" Such", f"in the mistake'.{fn(12)} Such"),
        ("the symbolic order.l) It is not", f"the symbolic order.{fn(13)} It is not"),
        ("outlive him.\" 4 This is why", f"outlive him.'{fn(14)} This is why"),
        ("five minutes ago.'15", f"five minutes ago.'{fn(15)}"),
        ("shock of the Real.'6", f"shock of the Real.{fn(16)}"),
        ("schema of it:17", f"schema of it:{fn(17)}"),
        ("subject presumed to believe.I8", f"subject presumed to believe.{fn(18)}"),
        ("suijea presumed to ergo/.'9", f"subject presumed to enjoy.{fn(19)}"),
        ("error itself?'o", f"error itself?{fn(20)}"),
        ("appearance qua appearance.'''", f"appearance qua appearance.'{fn(21)}"),
        ("own emptiness.\" The supersensible", f"own emptiness.{fn(22)} The supersensible"),
        ("gaze over the eye!J", f"gaze over the eye!]{fn(23)}"),
        ("which can be seen.\"! This is how", f"which can be seen.{fn(24)} This is how"),
        ("competing with his own.2S", f"competing with his own.{fn(25)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 5 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_five(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(201, 257):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 535:
                continue
            if pno > 201 and y0 < 55:
                continue
            if pno == 201 and y0 < 120:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(
                r"(?i)(which subject of the real\??|which subject of the reali|which subject of the realǨ|which subject of the reau|the sublime object of ideology|the sublim e o bject o f ideology|\d+|\d+ the sublime object of ideology|\d+ the sublime o bject of ideology|\d+ the sublime obj ect of ideology|the subject)\s*",
                cleaned,
            ):
                continue
            if re.match(r"^\d{1,2}\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)
    body = body.replace("Critique oJPractical Reason", "Critique of Practical Reason")
    body = body.replace("of Practical Reason.7", "of Practical Reason.7")
    body = body.replace("of formalization',9", "of formalization',9")
    body = body.replace("subject, but in the 1970s", "subject, but in the 1970s")
    body = insert_chapter_five_footnotes(body)
    body = body.replace(" Imaginary a Here, we", "\n\n@@figure:encore-schema\n\nHere, we", 1)

    headings = [
        ("'There is no metalanguage'", "'There Is No Metalanguage'", "h3"),
        ("The phallic signifier", "The Phallic Signifier", "h4"),
        ("'Lenin in Warsaw' as object", "'Lenin in Warsaw' as Object", "h4"),
        ("Antagonism as Real", "Antagonism as Real", "h4"),
        ("The forced choice of freedom", "The Forced Choice of Freedom", "h4"),
        ("Another Hegelian joke", "Another Hegelian Joke", "h4"),
        ("Subject as an 'answer of the Real'", "Subject as an 'Answer of the Real'", "h3"),
        ("S(Ⱥ), a, $", "S(Ⱥ), a, $", "h4"),
        ("The presumed to ...", "The Presumed to ...", "h4"),
        ("The presumed knowledge", "The Presumed Knowledge", "h4"),
        ("The supersensible is therefore appearance qua appearance", "The Supersensible Is Therefore Appearance Qua Appearance", "h4"),
    ]
    for raw, title, level in headings:
        body = body.replace(raw, f"\n\n@@{level}:{title}\n\n", 1)

    starters = [
        "In comprehending",
        "Post-structuralism claims",
        "In post-structuralism",
        "As Habermas",
        "In contrast",
        "Lacan always",
        "Actually",
        "Even at",
        "The post-structuralist",
        "On the one hand",
        "Is such",
        "To put",
        "How can",
        "That is why",
        "The whole",
        "The grand",
        "What is",
        "Lacan is close",
        "Metalanguage is",
        "For Derrida",
        "The Lacanian",
        "Let us",
        "The message",
        "Instead of",
        "Fenichel's",
        "In this way",
        "This is",
        "One must",
        "Here the title",
        "The field",
        "We can take",
        "It is only",
        "The same",
        "Take a short",
        "So, even",
        "But this",
        "With the development",
        "The Real is",
        "What all these",
        "To explain",
        "This 'real object'",
        "The use",
        "Perhaps we could",
        "In other words",
        "We could say",
        "The forced choice",
        "And it is",
        "The Kantian",
        "Here we have",
        "If we were",
        "Lacan gives",
        "What notion",
        "To get",
        "Here we have",
        "This paradox",
        "Ernesto Laclau",
        "Here, however",
        "In 'post-structuralism'",
        "But with Lacan",
        "To put it simply",
        "Our predominant",
        "The usual conclusion",
        "The Rabinovitch",
        "Adorno starts",
        "But in a dialectical",
        "This is what",
        "Such a paradoxical",
        "When a subject",
        "What, then",
        "At first sight",
        "But the Lacanian",
        "It is not",
        "It is clear",
        "Even if",
        "This obscene",
        "The process",
        "The subject",
        "Indeed",
        "This is why",
        "For example",
        "Some of us",
        "How do we",
        "There are",
        "The first",
        "Another kind",
        "Finally",
        "This mystery",
        "Coming from",
        "At first sight",
        "Each participant",
        "At this point",
        "No wonder",
        "The second",
        "The last",
        "The crucial",
        "Hitchcock's",
        "The word",
        "Contrary to",
        "Sydney Pollack's",
        "There is",
        "A hysterical",
        "To a hysterical",
        "However",
        "In the chapter",
        "The appearance",
        "But what",
        "With Hegel",
        "The illusion",
        "The supersensible",
        "Buñuel's films",
        "What the object",
        "The paradox",
        "In a first approach",
        "To conceive",
        "We can deceive",
        "This is how",
        "The real danger",
        "Stalinist Communism",
        "On the other hand",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = body.replace(" • ", "\n\n• ")
    body = body.replace(" •\n\n", "\n\n• ")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def insert_chapter_six_footnotes(body: str) -> str:
    fn = lambda n: footnote_popover(n, CHAPTER_SIX_FOOTNOTES, "ch6-")
    replacements = [
        ("Hegel's own dialectical procedure.' This inconsistency", f"Hegel's own dialectical procedure.'{fn(1)} This inconsistency"),
        ("mediation of displeasure'! In short", f"mediation of displeasure'{fn(2)} In short"),
        ("presentation {DarstellungJ of ideas.l It is", f"presentation [Darstellung] of ideas.{fn(3)} It is"),
        ("for us a law.4", f"for us a law.{fn(4)}"),
        ("felt for their religion when comparing themselves with others.' In what", f"felt for their religion when comparing themselves with others.'{fn(5)} In what"),
        ("a mere Thing.6", f"a mere Thing.{fn(6)}"),
        ("its limit is its positive condition. The Hegelian 'idealist wager'", f"its limit is its positive condition.{fn(7)} The Hegelian 'idealist wager'"),
        ("heroism of flattery.8", f"heroism of flattery.{fn(8)}"),
        ("has to be performed'.9", f"has to be performed'.{fn(9)}"),
        ("Positing, External, Determinate Reflection", f"Positing, External, Determinate Reflection{fn(10)}"),
        ("produced by consciousness.\" Before we intervene", f"produced by consciousness.\"{fn(11)} Before we intervene"),
        ("act of destruction. 12", f"act of destruction.{fn(12)}"),
        ("incessant activity.!l", f"incessant activity.{fn(13)}"),
        ("decrees and laws.14", f"decrees and laws.{fn(14)}"),
        ("positing reflection: '5", f"positing reflection:'{fn(15)}"),
    ]
    missing = []
    for old, new in replacements:
        if old not in body:
            missing.append(old)
            continue
        body = body.replace(old, new, 1)
    if missing:
        raise RuntimeError("Could not locate Chapter 6 footnote markers:\n" + "\n".join(missing))
    return body


def extract_chapter_six(doc: fitz.Document) -> list[str]:
    chunks: list[str] = []
    for pno in range(257, 295):
        page = doc[pno]
        for block in sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0])):
            _x0, y0, _x1, _y1, text = block[:5]
            if y0 >= 540:
                continue
            if pno > 257 and y0 < 55:
                continue
            if pno == 257 and y0 < 130:
                continue
            cleaned = clean_text(text)
            if not cleaned:
                continue
            if re.fullmatch(
                r"(?i)('not only as substance'|not only as substance|but also as subject|the sublime object of ideology|the sublim e object of ideology|\d+|\d+ the sublime object of ideology|\d+ the sublime o bject of ideology|\d+ the sublime obj ect of ideology|the subject|index)\s*",
                cleaned,
            ):
                continue
            if re.match(r"^(\d{1,2}|z)\s+", cleaned):
                continue
            chunks.append(cleaned)

    body = " ".join(chunks)
    for old, new in REPLACEMENTS.items():
        body = body.replace(old, new)
    body = insert_chapter_six_footnotes(body)

    headings = [
        ("The logic of sublimity", "The Logic of Sublimity", "h3"),
        ("'The Spirit is a bone'", "'The Spirit Is a Bone'", "h3"),
        ("Positing, External, Determinate Reflection", "Positing, External, Determinate Reflection", "h3"),
        ("The 'beautiful soul'", "The 'Beautiful Soul'", "h4"),
        ("The Monarch", "The Monarch", "h4"),
        ("Presupposing the positing", "Presupposing the Positing", "h3"),
        ("Subjective destitution", "Subjective Destitution", "h3"),
    ]
    for raw, title, level in headings:
        body = body.replace(raw, f"\n\n@@{level}:{title}\n\n", 1)

    starters = [
        "In his essay",
        "This inconsistency",
        "According to",
        "Despite some",
        "Greek religion",
        "The Jewish",
        "It is something",
        "If Greek",
        "In using",
        "Above all",
        "In short",
        "This means",
        "It is a definition",
        "The feeling",
        "We can now",
        "Kant himself",
        "In what consists",
        "In Hegel's defence",
        "The Hegelian criticism",
        "Hegel's reproach",
        "Precisely when",
        "But here again",
        "The key to",
        "Where Kant",
        "In other words",
        "To exemplify",
        "At the immediate",
        "What are we",
        "The speculative",
        "In the first",
        "The bone",
        "The Hegelian",
        "And - here",
        "Phallus and speech",
        "But where",
        "Noble-minded consciousness",
        "This subjectivation",
        "It is not",
        "But here",
        "The paradoxical",
        "To resolve",
        "The 'heroism",
        "The problem",
        "The paradox",
        "The proposition",
        "The difference",
        "This paradox",
        "Kantian external",
        "The usual",
        "External reflection",
        "The third",
        "Here, then",
        "One can see",
        "The same goes",
        "The 'true'",
        "We achieve",
        "In other words",
        "The 'absolute",
        "This redoubling",
        "What is so",
        "This is what",
        "The main feature",
        "By means",
        "The crucial",
        "Before we",
        "Here the interest",
        "For the reality",
        "What does",
        "Before the subject",
        "In Kant's",
        "It is thus",
        "The current",
        "What we must",
        "The Hegelian",
        "But this",
        "So this",
        "The Monarch",
        "At this point",
        "This, however",
        "Let us now",
        "There is, however",
        "The usual interpretation",
        "But, as",
        "Let us refer",
        "The external",
        "Reflection as",
        "Here we encounter",
        "To accomplish",
        "As we have",
        "The second",
        "When, for example",
        "The classical",
        "The Hegelian answer",
        "This is the significance",
        "Now, perhaps",
        "What is",
        "In other words",
        "The final moment",
        "That is to say",
        "In Christianity",
    ]
    for starter in starters:
        body = body.replace(f" {starter}", f"\n\n{starter}")
    body = body.replace(" • ", "\n\n• ")
    body = body.replace(" •\n\n", "\n\n• ")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def main() -> None:
    doc = fitz.open(PDF_PATH)
    ensure_figure_assets(doc)
    preface_paragraphs = extract_preface(doc)
    introduction_paragraphs = extract_introduction(doc)
    chapter_one_paragraphs = extract_chapter_one(doc)
    chapter_two_paragraphs = extract_chapter_two(doc)
    chapter_three_paragraphs = extract_chapter_three(doc)
    chapter_four_paragraphs = extract_chapter_four(doc)
    chapter_five_paragraphs = extract_chapter_five(doc)
    chapter_six_paragraphs = extract_chapter_six(doc)
    used_heading_ids = {
        "contents",
        "title",
        "preface",
        "introduction",
        "part-i",
        "chapter-1",
        "chapter-2",
        "part-ii",
        "chapter-3",
        "chapter-4",
        "part-iii",
        "chapter-5",
        "chapter-6",
        "footnotes",
    }

    def heading_text(title: str) -> str:
        return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title))).strip()

    def heading_id(prefix: str, title: str) -> str:
        seed = f"{prefix} {heading_text(title)}"
        base = re.sub(r"[^a-z0-9]+", "-", seed.lower()).strip("-") or "section"
        id_ = base
        counter = 2
        while id_ in used_heading_ids:
            id_ = f"{base}-{counter}"
            counter += 1
        used_heading_ids.add(id_)
        return id_

    def append_generated_heading(level: int, prefix: str, title: str) -> None:
        parts.append(f'<h{level} id="{heading_id(prefix, title)}">{title}</h{level}>')

    def collect_nav_headings() -> list[Heading]:
        heading_pattern = re.compile(r'<h([234]) id="([^"]+)">(.+)</h\1>')
        headings: list[Heading] = []
        for part in parts:
            match = heading_pattern.fullmatch(part)
            if not match:
                continue
            level, id_, title = int(match.group(1)), match.group(2), heading_text(match.group(3))
            if id_ == "footnotes":
                continue
            headings.append(Heading(level, title, id_))
        return headings

    parts = [
        "<section>",
        '<h1 id="title">The Sublime Object<br>of Ideology</h1>',
        '<p class="author">SLAVOJ ŽIŽEK</p>',
        '<p class="publisher">VERSO<br>London - New York</p>',
        "</section>",
        '<section aria-labelledby="preface">',
        '<h2 id="preface">Preface to the New Edition:<br><em>The Idea\'s Constipation?</em></h2>',
    ]

    for paragraph in preface_paragraphs:
        escaped = html.escape(paragraph, quote=False)
        escaped = re.sub(
            r"&lt;sup id=\"fnref-(\d+)\"&gt;&lt;a href=\"#fn-\1\"&gt;\1&lt;/a&gt;&lt;/sup&gt;",
            lambda m: footnote_popover(int(m.group(1))),
            escaped,
        )
        parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="introduction">',
        '<h2 id="introduction">Introduction</h2>',
    ]

    for paragraph in introduction_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="part-i">',
        '<h2 id="part-i">Part I<br>The Symptom</h2>',
        "</section>",
        '<section aria-labelledby="chapter-1">',
        '<h2 id="chapter-1">1. How Did Marx Invent the Symptom?</h2>',
    ]

    for paragraph in chapter_one_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-1", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="chapter-2">',
        '<h2 id="chapter-2">2. From Symptom to Sinthome</h2>',
    ]

    for paragraph in chapter_two_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-2", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("@@h4:"):
            append_generated_heading(4, "chapter-2", escaped.removeprefix("@@h4:"))
        elif escaped.startswith("@@figure:"):
            parts.append(figure_html(escaped.removeprefix("@@figure:")))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="part-ii">',
        '<h2 id="part-ii">Part II<br>Lack in the Other</h2>',
        "</section>",
        '<section aria-labelledby="chapter-3">',
        '<h2 id="chapter-3">3. ‘Che Vuoi?’</h2>',
    ]

    for paragraph in chapter_three_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-3", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("@@h4:"):
            append_generated_heading(4, "chapter-3", escaped.removeprefix("@@h4:"))
        elif escaped.startswith("@@figure:"):
            parts.append(figure_html(escaped.removeprefix("@@figure:")))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="chapter-4">',
        '<h2 id="chapter-4">4. You Only Die Twice</h2>',
    ]

    for paragraph in chapter_four_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-4", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("@@h4:"):
            append_generated_heading(4, "chapter-4", escaped.removeprefix("@@h4:"))
        elif escaped.startswith("@@figure:"):
            parts.append(figure_html(escaped.removeprefix("@@figure:")))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="part-iii">',
        '<h2 id="part-iii">Part III<br>The Subject</h2>',
        "</section>",
        '<section aria-labelledby="chapter-5">',
        '<h2 id="chapter-5">5. Which Subject of the Real?</h2>',
    ]

    for paragraph in chapter_five_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-5", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("@@h4:"):
            append_generated_heading(4, "chapter-5", escaped.removeprefix("@@h4:"))
        elif escaped.startswith("@@figure:"):
            parts.append(figure_html(escaped.removeprefix("@@figure:")))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section aria-labelledby="chapter-6">',
        '<h2 id="chapter-6">6. ‘Not Only as Substance, but Also as Subject’</h2>',
    ]

    for paragraph in chapter_six_paragraphs:
        escaped = escape_with_inline_html(paragraph)
        if escaped.startswith("@@h3:"):
            append_generated_heading(3, "chapter-6", escaped.removeprefix("@@h3:"))
        elif escaped.startswith("@@h4:"):
            append_generated_heading(4, "chapter-6", escaped.removeprefix("@@h4:"))
        elif escaped.startswith("•"):
            parts.append(f'<p class="bullet">{escaped[1:].strip()}</p>')
        else:
            parts.append(f"<p>{escaped}</p>")

    parts += [
        "</section>",
        '<section class="footnotes" aria-labelledby="footnotes">',
        '<h2 id="footnotes">Footnotes</h2>',
        "<ol>",
    ]
    for num, note in FOOTNOTES.items():
        parts.append(f'<li id="fn-{num}">{html.escape(note, quote=False)} <a class="backref" href="#fnref-{num}">↩</a></li>')
    for num, note in INTRO_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-intro-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-intro-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_ONE_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch1-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch1-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_TWO_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch2-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch2-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_THREE_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch3-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch3-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_FOUR_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch4-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch4-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_FIVE_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch5-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch5-{num}">↩</a></li>'
        )
    for num, note in CHAPTER_SIX_FOOTNOTES.items():
        parts.append(
            f'<li id="fn-ch6-{num}">{num}. {html.escape(note, quote=False)} '
            f'<a class="backref" href="#fnref-ch6-{num}">↩</a></li>'
        )
    parts += [
        "</ol>",
        "</section>",
    ]

    nav_headings = [Heading(2, "Title", "title"), Heading(2, "Contents", "contents"), *collect_nav_headings()]
    parts.insert(5, render_linked_contents(nav_headings))
    markup = wrap_html_document(
        "The Sublime Object of Ideology - Front Matter",
        "\n".join(parts),
        render_standard_nav(nav_headings),
        css=STANDARD_BOOK_CSS,
        script=FOOTNOTE_SCRIPT,
    )
    OUTPUT_PATH.write_text(markup, encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
