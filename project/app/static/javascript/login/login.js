document.addEventListener("DOMContentLoaded", function() {
    const toggleLinkToSignup = document.getElementById("toggle-link-to-signup");
    const toggleLinkToLogin = document.getElementById("toggle-link-to-login");
    const signinForm = document.getElementById("signin");
    const signupForm = document.getElementById("signup");
    const infoContainer = document.getElementById("info-container");
    const cardLogin = document.getElementById("card-login");
    const cardSignup = document.getElementById("card-signup");
    const formTitle = document.getElementById("form-title");
    const formDescription = document.getElementById("form-description");

    toggleLinkToSignup.addEventListener("click", function(event) {
        event.preventDefault();
        signupForm.classList.remove('form-inactive');
        signupForm.classList.add('form-active');
        signinForm.classList.remove('form-active');
        signinForm.classList.add('form-inactive');

        formTitle.textContent = "CADASTRO";
        formDescription.textContent = "Cadastre-se para criar sua conta no SecureSight";
        
        infoContainer.classList.remove('red');
        infoContainer.classList.add('blue');
        cardLogin.classList.add('hidden');
        cardSignup.classList.remove('hidden');
    });

    toggleLinkToLogin.addEventListener("click", function(event) {
        event.preventDefault();
        signinForm.classList.remove('form-inactive');
        signinForm.classList.add('form-active');
        signupForm.classList.remove('form-active');
        signupForm.classList.add('form-inactive');

        formTitle.textContent = "LOGIN";
        formDescription.textContent = "Entre com sua conta em SecureSight";
        
        infoContainer.classList.remove('blue');
        infoContainer.classList.add('red');
        cardSignup.classList.add('hidden');
        cardLogin.classList.remove('hidden');
    });
});

document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById("plan-modal");
    var span = document.getElementsByClassName("close")[0];
    var infoContainer = document.getElementById("info-container");

    function showModal() {
        modal.style.display = "block";
    }

    function hideModal() {
        modal.style.display = "none";
    }

    span.onclick = hideModal;

    window.onclick = function (event) {
        if (event.target == modal) {
            hideModal();
        }
    }

    function checkSubscription() {
        // Obtém o e-mail do usuário do contexto da página
        const userEmail = window.userEmail;

        console.log('E-mail do usuário:', userEmail); // Mensagem de depuração

        if (!userEmail) {
            console.error('O e-mail do usuário não está definido.');
            return;
        }

        fetch(`/api/check-subscription?email=${encodeURIComponent(userEmail)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Falha na resposta da API');
                }
                return response.json();
            })
            .then(data => {
                console.log('Resposta da API:', data); // Mensagem de depuração

                if (!data.isSubscriber) {
                    showModal(); // Exibe o modal se o usuário não for assinante
                    infoContainer.style.display = 'none'; // Oculta a mensagem se o modal estiver sendo exibido
                } else {
                    window.location.href = '/user-int'; // Redireciona para user-int se o usuário tem plano ativo
                }
            })
            .catch(error => console.error('Erro ao verificar assinatura:', error));
    }

    checkSubscription();
});
