var formSignin = document.querySelector('#signin')
var formSignup = document.querySelector('#signup')
var btnColor = document.querySelector('.btnColor')

document.querySelector('#btnSignin')
  .addEventListener('click', () => {
    formSignin.style.left = "25px"
    formSignup.style.left = "450px"
    btnColor.style.left = "0px"
})

document.querySelector('#btnSignup')
  .addEventListener('click', () => {
    formSignin.style.left = "-450px"
    formSignup.style.left = "25px"
    btnColor.style.left = "114px"
})

document.addEventListener('DOMContentLoaded', function() {
  const errorModal = document.getElementById('errorModal');
  const errorText = document.getElementById('errorText');
  const closeBtn = errorModal.querySelector('.close');

  function openErrorModal(message) {
      errorText.innerText = message;
      errorModal.style.display = 'block';
  }

  function closeErrorModal() {
      errorModal.style.display = 'none';
  }

  // Fechar modal ao clicar no botão de fechar
  closeBtn.addEventListener('click', closeErrorModal);

});
