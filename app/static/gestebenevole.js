
function showForm(formOverlay) {
    document.getElementById(formOverlay).classList.add('active');
}

function hideForm(formOverlay) {
    document.getElementById(formOverlay).classList.remove('active');
}

// select list
jQuery(document).ready(function ($) {
    $(".clickable-row").click(function () {
        window.location = $(this).data("href");
    });
    $('#mySelect').select2();
});

// date formatting
for (let el of document.querySelectorAll(".date, .added, .birth")) {
    el.textContent = new Date(el.textContent).toLocaleDateString('fr-FR');
}

// search in tables
new List('entries', { valueNames: ["name", "firstname", "lastname", "category", "email", "date", "patient", "notes", "added", "birth"] });

// specific to drugstore in prescriptions
var drugstoreSearch = document.getElementById('drugstore-search');
if (drugstoreSearch) {
    var drugstoreValue = document.getElementById('drugstore-value');
    var drugstoreDataset = document.getElementById("drugstore-dataset");
    var drugstoreTable = document.getElementById("drugstore-table");
    drugstoreSearch.addEventListener('keyup', function () {
        var drug = drugstoreSearch.value.trim();

        drugstoreTable.querySelectorAll('tr').forEach(element => {
            drugstoreTable.removeChild(element);
        });
        if (drug.length < 3) { return; }

        drugstoreDataset.querySelectorAll('div').forEach(function (item) {
            if (item.dataset.name.toLowerCase().includes(drug.toLowerCase())) {
                var tr = document.createElement('tr');
                // on click on the row, the drugstore id is stored in the hidden input
                tr.addEventListener('click', function () {
                    drugstoreValue.value = item.dataset.id;
                    drugstoreSearch.value = item.dataset.name;
                    drugstoreTable.querySelectorAll('tr').forEach(element => {
                        drugstoreTable.removeChild(element);
                    });
                }
                );
                tr.innerHTML = '<td class="clickable-row" value="' + item.dataset.id + '">' + item.dataset.name + '</td>';
                drugstoreTable.appendChild(tr);
            }
        }
        );
    }
    );
}


// auto-logout
var maxIdleTime = 900000;
var logoutUrl = "/logout";

var idleTimer;
function resetTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(redirectToLogout, maxIdleTime);
}

function redirectToLogout() {
    window.location.href = logoutUrl;
}

window.onload = resetTimer;
window.onmousemove = resetTimer;
window.onmousedown = resetTimer;
window.onclick = resetTimer;
window.onscroll = resetTimer;
window.onkeypress = resetTimer;

window.addEventListener('popstate', function (event) {
    location.reload();
});