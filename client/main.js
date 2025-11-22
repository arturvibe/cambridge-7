// Replace with your Firebase project's configuration
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// Initialize Firebase
const app = firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

const loginContainer = document.getElementById('login-container');
const userContainer = document.getElementById('user-container');
const loginButton = document.getElementById('login-button');
const logoutButton = document.getElementById('logout-button');
const emailInput = document.getElementById('email');
const userEmailSpan = document.getElementById('user-email');

loginButton.addEventListener('click', () => {
    const email = emailInput.value;
    const actionCodeSettings = {
        url: window.location.href,
        handleCodeInApp: true
    };
    auth.sendSignInLinkToEmail(email, actionCodeSettings)
        .then(() => {
            window.localStorage.setItem('emailForSignIn', email);
            alert('Magic link sent to your email!');
        })
        .catch((error) => {
            alert(`Error sending magic link: ${error.message}`);
        });
});

logoutButton.addEventListener('click', () => {
    fetch('/auth/logout', { method: 'POST' })
        .then(() => {
            auth.signOut();
            userContainer.style.display = 'none';
            loginContainer.style.display = 'block';
        });
});

// Handle the sign-in redirect
if (auth.isSignInWithEmailLink(window.location.href)) {
    let email = window.localStorage.getItem('emailForSignIn');
    if (!email) {
        email = window.prompt('Please provide your email for confirmation');
    }
    auth.signInWithEmailLink(email, window.location.href)
        .then((result) => {
            window.localStorage.removeItem('emailForSignIn');
            result.user.getIdToken().then((idToken) => {
                fetch('/auth/session-login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ id_token: idToken })
                }).then(response => {
                    if (response.ok) {
                        loginContainer.style.display = 'none';
                        userContainer.style.display = 'block';
                        userEmailSpan.textContent = result.user.email;
                    }
                });
            });
        })
        .catch((error) => {
            alert(`Error signing in: ${error.message}`);
        });
}

// Check for existing session
auth.onAuthStateChanged((user) => {
    if (user) {
        loginContainer.style.display = 'none';
        userContainer.style.display = 'block';
        userEmailSpan.textContent = user.email;
    } else {
        loginContainer.style.display = 'block';
        userContainer.style.display = 'none';
    }
});
