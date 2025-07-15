document.addEventListener("DOMContentLoaded", function () {
    const studentTableBlock = document.getElementById('student-table');
    const analysisBlock = document.getElementById('student-analysis');
    const outputBlock = document.getElementById('output');
    const form = document.getElementById('analysis-form');
    const motivatedForm = document.getElementById('motivated-form');
    const motivatedResults = document.getElementById('motivated-results');
    const preloader = document.getElementById('preloader');

    function showLoader() {
        if (preloader) preloader.style.display = 'block';
    }

    function hideLoader() {
        if (preloader) preloader.style.display = 'none';
    }

    // Tab switching
    document.querySelectorAll('#analysisTabs .nav-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelectorAll('#analysisTabs .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            document.querySelectorAll('.tab-pane').forEach(pane => pane.style.display = 'none');
            const targetTab = link.getAttribute('data-tab');
            document.getElementById(targetTab).style.display = 'block';

            if (targetTab === 'tab-all-students') {
                fetchStudents(1);
            }
        });
    });

    // Load student table
    window.fetchStudents = async function (page = 1) {
        showLoader();
        analysisBlock.innerHTML = '';
        studentTableBlock.innerHTML = '<p>Loading students...</p>';
        const response = await fetch(`/students?page=${page}`);
        studentTableBlock.innerHTML = await response.text();
        hideLoader();
    };

    // Analysis per student (from table)
    window.showAnalysis = async function (email) {
        showLoader();
        const weekFrom = document.getElementById('week_from').value;
        const weekTo = document.getElementById('week_to').value;
        const action = 'analyse_student';

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
        hideLoader();
    };

    // Check by student form
    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();

            showLoader();
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
            hideLoader();
        });
    }

    // Motivated Students form
    if (motivatedForm) {
        motivatedForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            showLoader();
            motivatedResults.innerHTML = '<p>Loading...</p>';

            const type = document.getElementById('motivated-type').value;
            const number = document.getElementById('motivated-number').value;
            const weekFrom = document.getElementById('motivated-week-from').value;
            const weekTo = document.getElementById('motivated-week-to').value;

            const payload = {
                action: type,
                week_from: weekFrom,
                week_to: weekTo,
                num_students: number
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
                motivatedResults.innerHTML = data.html;
            } else {
                motivatedResults.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
            }

            hideLoader();
        });
    }

    // Auto-load default tab
    document.querySelector('#analysisTabs .nav-link.active').click();
});