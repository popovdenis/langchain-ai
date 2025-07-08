document.addEventListener("DOMContentLoaded", function () {
    const studentTypeRadios = document.querySelectorAll('input[name="student_type"]');
    const emailInputBlock = document.getElementById('student-email-input');
    const studentTableBlock = document.getElementById('student-table');
    const analysisBlock = document.getElementById('student-analysis');
    const outputBlock = document.getElementById('output');
    const form = document.getElementById('analysis-form');

    function toggleStudentType() {
        const selected = document.querySelector('input[name="student_type"]:checked').value;
        outputBlock.innerHTML = "";
        analysisBlock.innerHTML = "";
        if (selected === 'email') {
            emailInputBlock.style.display = 'block';
            studentTableBlock.innerHTML = '';
        } else {
            emailInputBlock.style.display = 'none';
            fetchStudents(1);
        }
    }

    studentTypeRadios.forEach(radio => {
        radio.addEventListener('change', toggleStudentType);
    });

    async function fetchStudents(page = 1) {
        studentTableBlock.innerHTML = '<p>Loading students...</p>';
        try {
            const response = await fetch(`/students?page=${page}`);
            const html = await response.text();
            studentTableBlock.innerHTML = html;
        } catch (err) {
            studentTableBlock.innerHTML = '<p>Error loading students</p>';
        }
    }

    window.showAnalysis = async function (email) {
        analysisBlock.innerHTML = '<p>Loading analysis...</p>';

        const weekFrom = document.getElementById('week_from').value;
        const weekTo = document.getElementById('week_to').value;
        const action = document.getElementById('action').value;

        const payload = {
            action: action,
            email: email,
            week_from: weekFrom,
            week_to: weekTo
        };

        try {
            const response = await fetch("/analysis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            analysisBlock.innerHTML = data.html;
        } catch (err) {
            analysisBlock.innerHTML = "<p>Error loading analysis</p>";
        }
    };

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        outputBlock.innerHTML = '<p>Loading...</p>';

        const email = document.getElementById('email').value;
        const weekFrom = document.getElementById('week_from').value;
        const weekTo = document.getElementById('week_to').value;
        const action = document.getElementById('action').value;

        const payload = {
            action: action,
            email: email,
            week_from: weekFrom,
            week_to: weekTo
        };

        try {
            const response = await fetch("/analysis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            outputBlock.innerHTML = data.html;
        } catch (err) {
            outputBlock.innerHTML = "<p>Error loading analysis</p>";
        }
    });

    toggleStudentType();
});