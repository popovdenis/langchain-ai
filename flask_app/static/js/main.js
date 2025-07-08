document.addEventListener("DOMContentLoaded", function () {
    const studentTypeRadios = document.querySelectorAll('input[name="student_type"]');
    const emailInputBlock = document.getElementById('student-email-block');
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

    window.fetchStudents = async function (page = 1) {
        analysisBlock.innerHTML = '';
        studentTableBlock.innerHTML = '<p>Loading students...</p>';
        const response = await fetch(`/students?page=${page}`);
        const html = await response.text();
        studentTableBlock.innerHTML = html;
    };

    window.showAnalysis = async function (email) {
        studentTableBlock.innerHTML = '';
        analysisBlock.innerHTML = '<p>Loading analysis...</p>';

        const weekFrom = document.getElementById('week_from').value;
        const weekTo = document.getElementById('week_to').value;
        const action = document.getElementById('action').value;

        const payload = {
            action,
            email,
            week_from: weekFrom,
            week_to: weekTo,
            num_students: 1
        };

        const response = await fetch("/analysis", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.html) {
            analysisBlock.innerHTML = data.html;
        } else {
            analysisBlock.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
        }
    };

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        outputBlock.innerHTML = '<p>Loading analysis...</p>';

        const formData = new FormData(form);
        const payload = {
            action: formData.get('action'),
            email: formData.get('email'),
            week_from: formData.get('week_from'),
            week_to: formData.get('week_to'),
            num_students: 1
        };

        const response = await fetch("/analysis", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.html) {
            outputBlock.innerHTML = data.html;
        } else {
            outputBlock.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
        }
    });

    toggleStudentType();
});