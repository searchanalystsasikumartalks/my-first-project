/* Editorial associations, not psychological measures. */
const QUESTIONS = [
  {
    "id": "flower",
    "title": "Which flower draws you in?",
    "hint": "Small details, different kinds of beauty.",
    "options": [
      {
        "id": "jasmine",
        "label": "Jasmine",
        "icon": "✿",
        "scene": "the quiet presence of jasmine",
        "theme": "quiet beauty"
      },
      {
        "id": "rose",
        "label": "Rose",
        "icon": "❀",
        "scene": "the expressive shape of a rose",
        "theme": "warm expression"
      },
      {
        "id": "sunflower",
        "label": "Sunflower",
        "icon": "☀",
        "scene": "a sunflower turning toward the light",
        "theme": "bright possibility"
      },
      {
        "id": "lotus",
        "label": "Lotus",
        "icon": "❋",
        "scene": "a lotus resting above the water",
        "theme": "a moment of stillness"
      }
    ]
  },
  {
    "id": "fruit",
    "title": "Pick a fruit you enjoy.",
    "hint": "Go with taste, color, or a happy memory.",
    "options": [
      {
        "id": "mango",
        "label": "Mango",
        "icon": "🥭",
        "scene": "the rich sweetness of mango",
        "theme": "simple pleasure"
      },
      {
        "id": "apple",
        "label": "Apple",
        "icon": "🍎",
        "scene": "the familiar crunch of an apple",
        "theme": "everyday comforts"
      },
      {
        "id": "orange",
        "label": "Orange",
        "icon": "🍊",
        "scene": "the fresh brightness of an orange",
        "theme": "fresh beginnings"
      },
      {
        "id": "grapes",
        "label": "Grapes",
        "icon": "🍇",
        "scene": "a handful of grapes",
        "theme": "small moments worth savoring"
      }
    ]
  },
  {
    "id": "color",
    "title": "Which color feels right today?",
    "hint": "There is no hidden right answer.",
    "options": [
      {
        "id": "blue",
        "label": "Blue",
        "icon": "🔵",
        "scene": "a spacious blue palette",
        "theme": "breathing room"
      },
      {
        "id": "green",
        "label": "Green",
        "icon": "🟢",
        "scene": "a green palette",
        "theme": "a connection to living things"
      },
      {
        "id": "yellow",
        "label": "Yellow",
        "icon": "🟡",
        "scene": "a sunny yellow palette",
        "theme": "playful energy"
      },
      {
        "id": "purple",
        "label": "Purple",
        "icon": "🟣",
        "scene": "a purple palette",
        "theme": "room for imagination"
      }
    ]
  },
  {
    "id": "sky",
    "title": "Moon or sun? Or something else?",
    "hint": "Choose the scene you would pause to watch.",
    "options": [
      {
        "id": "moon",
        "label": "Moon",
        "icon": "☾",
        "scene": "the soft light of the moon",
        "theme": "gentleness"
      },
      {
        "id": "sun",
        "label": "Sun",
        "icon": "☀",
        "scene": "the clear light of the sun",
        "theme": "visible energy"
      },
      {
        "id": "stars",
        "label": "Stars",
        "icon": "✧",
        "scene": "a sky full of stars",
        "theme": "curiosity"
      },
      {
        "id": "clouds",
        "label": "Clouds",
        "icon": "☁",
        "scene": "clouds changing shape",
        "theme": "openness to change"
      }
    ]
  },
  {
    "id": "place",
    "title": "Where would you take a little break?",
    "hint": "Imagine a place, not a travel budget.",
    "options": [
      {
        "id": "sea",
        "label": "By the sea",
        "icon": "≈",
        "scene": "time beside the sea",
        "theme": "perspective"
      },
      {
        "id": "forest",
        "label": "In a forest",
        "icon": "♧",
        "scene": "a forest path",
        "theme": "unhurried attention"
      },
      {
        "id": "mountain",
        "label": "In the mountains",
        "icon": "△",
        "scene": "a mountain view",
        "theme": "a wider horizon"
      },
      {
        "id": "city",
        "label": "In a lively city",
        "icon": "▥",
        "scene": "a lively city street",
        "theme": "discovery"
      }
    ]
  },
  {
    "id": "weather",
    "title": "Choose your kind of weather.",
    "hint": "A mood for an imaginary day.",
    "options": [
      {
        "id": "rain",
        "label": "Gentle rain",
        "icon": "☂",
        "scene": "gentle rain",
        "theme": "a slower rhythm"
      },
      {
        "id": "breeze",
        "label": "A cool breeze",
        "icon": "≋",
        "scene": "a cool breeze",
        "theme": "lightness"
      },
      {
        "id": "sunshine",
        "label": "Warm sunshine",
        "icon": "☼",
        "scene": "warm sunshine",
        "theme": "an open invitation"
      },
      {
        "id": "snow",
        "label": "Falling snow",
        "icon": "❄",
        "scene": "falling snow",
        "theme": "a fresh perspective"
      }
    ]
  },
  {
    "id": "sound",
    "title": "What would you like to hear?",
    "hint": "Build the soundtrack to your moment.",
    "options": [
      {
        "id": "waves",
        "label": "Ocean waves",
        "icon": "≈",
        "scene": "the sound of waves",
        "theme": "a steady rhythm"
      },
      {
        "id": "birds",
        "label": "Birdsong",
        "icon": "♪",
        "scene": "birdsong",
        "theme": "noticing small details"
      },
      {
        "id": "music",
        "label": "Favorite music",
        "icon": "♫",
        "scene": "favorite music",
        "theme": "personal expression"
      },
      {
        "id": "quiet",
        "label": "Quiet",
        "icon": "◦",
        "scene": "a quiet space",
        "theme": "room to think"
      }
    ]
  },
  {
    "id": "pastime",
    "title": "Choose an afternoon activity.",
    "hint": "Pick what appeals to you right now.",
    "options": [
      {
        "id": "read",
        "label": "Read a story",
        "icon": "▤",
        "scene": "reading a story",
        "theme": "exploring another perspective"
      },
      {
        "id": "make",
        "label": "Make something",
        "icon": "✎",
        "scene": "making something",
        "theme": "trying an idea by hand"
      },
      {
        "id": "walk",
        "label": "Go for a walk",
        "icon": "↟",
        "scene": "taking a walk",
        "theme": "following your curiosity"
      },
      {
        "id": "talk",
        "label": "Talk with a friend",
        "icon": "☏",
        "scene": "talking with a friend",
        "theme": "shared attention"
      }
    ]
  },
  {
    "id": "season",
    "title": "Pick a season for your story.",
    "hint": "Any season can hold more than one feeling.",
    "options": [
      {
        "id": "spring",
        "label": "Spring",
        "icon": "❀",
        "scene": "spring",
        "theme": "new possibilities"
      },
      {
        "id": "summer",
        "label": "Summer",
        "icon": "☀",
        "scene": "summer",
        "theme": "a little expansiveness"
      },
      {
        "id": "autumn",
        "label": "Autumn",
        "icon": "❧",
        "scene": "autumn",
        "theme": "noticing change"
      },
      {
        "id": "winter",
        "label": "Winter",
        "icon": "❄",
        "scene": "winter",
        "theme": "a quieter pace"
      }
    ]
  },
  {
    "id": "object",
    "title": "One last detail: choose a keepsake.",
    "hint": "What would you place on a favorite shelf?",
    "options": [
      {
        "id": "book",
        "label": "A book",
        "icon": "▤",
        "scene": "a well-loved book",
        "theme": "stories you can return to"
      },
      {
        "id": "shell",
        "label": "A shell",
        "icon": "◔",
        "scene": "a shell",
        "theme": "memories of a place"
      },
      {
        "id": "photo",
        "label": "A photograph",
        "icon": "▣",
        "scene": "a photograph",
        "theme": "moments with meaning"
      },
      {
        "id": "stone",
        "label": "A smooth stone",
        "icon": "●",
        "scene": "a smooth stone",
        "theme": "simple, tangible comforts"
      }
    ]
  }
];
