const moodOptions = document.querySelectorAll(".mood-option");
const paletteOptions = document.querySelectorAll(".palette-option");
const styleOptions = document.querySelectorAll(".style-option");
const energyOptions = document.querySelectorAll(".energy-option");
const progressSegments = document.querySelectorAll(".progress-segment");

let selectedMood = null;
let selectedPalette = null;
let selectedStyle = null;
let selectedEnergy = null;
let currentQuestion = 1;

const continueButton = document.querySelector(".continue-button");

const questionText = document.querySelector("#question-text");

const progressText = document.querySelector("#progress-text");

moodOptions.forEach(function(option) {
    option.addEventListener("click", function() {
        moodOptions.forEach(function(mood) {
            mood.classList.remove("selected");
        });
        option.classList.add("selected");
        selectedMood = option.textContent.trim();
    });
});

paletteOptions.forEach(function(option) {
    option.addEventListener("click", function() {
        paletteOptions.forEach(function(palette) {
            palette.classList.remove("selected");
        });
        option.classList.add("selected");
        selectedPalette = option.textContent.trim();
    });
});

styleOptions.forEach(function(option) {
    option.addEventListener("click", function() {
        styleOptions.forEach(function(style) {
            style.classList.remove("selected");
        });

        option.classList.add("selected");
        selectedStyle = option.textContent.trim();
    });
});

energyOptions.forEach(function(option) {
    option.addEventListener("click", function() {
        energyOptions.forEach(function(energy) {
            energy.classList.remove("selected");
        });

        option.classList.add("selected");
        selectedEnergy = option.textContent.trim();
    });
});

const questionOne = document.querySelector(".question-one");
const questionTwo = document.querySelector(".question-two");
const questionThree = document.querySelector(".question-three");
const questionFour = document.querySelector(".question-four");

continueButton.addEventListener("click", function() {
    if (currentQuestion === 1 && selectedMood === null) {
        alert("Please select a mood before continuing.");
        return;
    }

    if (currentQuestion === 2 && selectedPalette === null) {
        alert("Please select a palette before continuing.");
        return;
    }

    if (currentQuestion === 3 && selectedStyle === null) {
        alert("Please select a style before continuing.");
        return;
    }

    if (currentQuestion === 4 && selectedEnergy === null) {
        alert("Please select your outfit's energy before continuing.");
        return;
    }

    questionOne.style.display = "none";
    questionTwo.style.display = "none";
    questionThree.style.display = "none";
    questionFour.style.display = "none";

    currentQuestion++;

    if (currentQuestion === 2) {
        questionTwo.style.display = "flex";
    } else if (currentQuestion === 3) {
        questionThree.style.display = "flex";
    } else if (currentQuestion === 4) {
        questionFour.style.display = "flex";
    } else {
        alert("You've completed the quiz!");
        currentQuestion = 4;
        return;
    }

    progressSegments.forEach(function(segment, index) {
        segment.classList.toggle("active", index < currentQuestion);
    });

    progressText.textContent =
        "Your color forecast - 0" + currentQuestion + " / 04";
});