document.addEventListener("DOMContentLoaded", function() {
    const toggleSwitch = document.querySelector('#darkModeSwitch');
    const body = document.body;
    const icon = document.querySelector('#themeIcon');

    if (toggleSwitch) {
        if (localStorage.getItem('theme') === 'dark') {
            body.classList.add('dark-mode');
            toggleSwitch.checked = true;
            if(icon) {
                icon.classList.remove('fa-moon', 'text-secondary');
                icon.classList.add('fa-sun', 'text-warning');
            }
        }

        toggleSwitch.addEventListener('change', function() {
            if (this.checked) {
                body.classList.add('dark-mode');
                localStorage.setItem('theme', 'dark');
                if(icon) {
                    icon.classList.remove('fa-moon', 'text-secondary');
                    icon.classList.add('fa-sun', 'text-warning');
                }
            } else {
                body.classList.remove('dark-mode');
                localStorage.setItem('theme', 'light');
                if(icon) {
                    icon.classList.remove('fa-sun', 'text-warning');
                    icon.classList.add('fa-moon', 'text-secondary');
                }
            }
        });
    }
});

//$(document).ready(function() {
//    if ($('.select2-dropdown').length > 0) {
//        $('.select2-dropdown').select2({
//            theme: "classic",
//            placeholder: "Select or Type...",
//            allowClear: true,
//            width: '100%'
//        });
//    }
//});