// Инициализация Telegram WebApp
let tgUser = null;
let initData = null;

if (window.Telegram && window.Telegram.WebApp) {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();

  tgUser = Telegram.WebApp.initDataUnsafe.user;
  initData = Telegram.WebApp.initData;
  
  console.log('Пользователь:', tgUser);
}

// Базовый URL для API
const API_BASE_URL = '/api'; // Замените на реальный URL вашего бота

// DOM элементы
const mainScreen = document.getElementById('main-screen');
const playScreen = document.getElementById('play-screen');
const profileScreen = document.getElementById('profile-screen');
const referralsScreen = document.getElementById('referrals-screen');
const titlesScreen = document.getElementById('titles-screen');
const bonusesScreen = document.getElementById('bonuses-screen');
const gameScreen = document.getElementById('game-screen');

// Кнопки главного меню
const playBtn = document.getElementById('play-btn');
const profileBtn = document.getElementById('profile-btn');
const referralsBtn = document.getElementById('referrals-btn');
const titlesBtn = document.getElementById('titles-btn');
const bonusesBtn = document.getElementById('bonuses-btn');

// Кнопки "Назад"
const backToMainFromPlay = document.getElementById('back-to-main-from-play');
const backToMainFromProfile = document.getElementById('back-to-main-from-profile');
const backToMainFromReferrals = document.getElementById('back-to-main-from-referrals');
const backToMainFromTitles = document.getElementById('back-to-main-from-titles');
const backToMainFromBonuses = document.getElementById('back-to-main-from-bonuses');
const backToPlay = document.getElementById('back-to-play');

// Игровые кнопки
const gameButtons = document.querySelectorAll('.game-btn');

// Загрузка данных пользователя
async function loadUserData() {
  if (!initData) {
    console.error('Telegram WebApp initData отсутствует');
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/user`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ initData })
    });

    const data = await response.json();
    
    if (data.success) {
      // Обновляем UI с данными пользователя
      document.getElementById('balance-amount').textContent = data.data.balance;
      document.getElementById('profile-balance').textContent = data.data.balance;
      document.getElementById('user-name').textContent = tgUser.first_name;
      document.getElementById('user-level').textContent = data.data.level;
      document.getElementById('user-rank').textContent = data.data.rank;
      document.getElementById('user-xp').textContent = data.data.xp;
      document.getElementById('xp-needed').textContent = data.data.xp_needed;
      
      // Обновляем прогресс XP
      const xpProgress = document.getElementById('xp-progress');
      const progressPercent = (data.data.xp / data.data.xp_needed) * 100;
      xpProgress.style.width = `${Math.min(progressPercent, 100)}%`;
      
      // Загружаем достижения
      loadAchievements(data.data.achievements);
      
      // Загружаем реферальную информацию
      loadReferralInfo(data.data.referral_link, data.data.referral_count);
    } else {
      console.error('Ошибка при получении данных пользователя:', data.message);
    }
  } catch (error) {
    console.error('Ошибка при загрузке данных пользователя:', error);
  }
}

// Загрузка достижений
function loadAchievements(achievements) {
  const achievementsList = document.getElementById('achievements-list');
  achievementsList.innerHTML = '';
  
  achievements.forEach(achievement => {
    const achievementElement = document.createElement('div');
    achievementElement.className = 'achievement-item';
    achievementElement.title = achievement.name;
    achievementElement.textContent = achievement.icon || '🏆';
    achievementsList.appendChild(achievementElement);
  });
}

// Загрузка реферальной информации
function loadReferralInfo(referralLink, referralCount) {
  document.getElementById('referral-link').textContent = referralLink;
  document.getElementById('referral-count').textContent = referralCount;
}

// Функция переключения экранов
function showScreen(screen) {
  // Скрываем все экраны
  const screens = document.querySelectorAll('.screen');
  screens.forEach(s => s.classList.remove('active'));
  
  // Показываем нужный экран
  screen.classList.add('active');
}

// Обработчики кнопок главного меню
playBtn.addEventListener('click', () => {
  showScreen(playScreen);
});

profileBtn.addEventListener('click', () => {
  loadUserData();
  showScreen(profileScreen);
});

referralsBtn.addEventListener('click', () => {
  showScreen(referralsScreen);
});

titlesBtn.addEventListener('click', () => {
  showScreen(titlesScreen);
});

bonusesBtn.addEventListener('click', () => {
  showScreen(bonusesScreen);
});

// Обработчики кнопок "Назад"
backToMainFromPlay.addEventListener('click', () => {
  showScreen(mainScreen);
});

backToMainFromProfile.addEventListener('click', () => {
  showScreen(mainScreen);
});

backToMainFromReferrals.addEventListener('click', () => {
  showScreen(mainScreen);
});

backToMainFromTitles.addEventListener('click', () => {
  showScreen(mainScreen);
});

backToMainFromBonuses.addEventListener('click', () => {
  showScreen(mainScreen);
});

backToPlay.addEventListener('click', () => {
  showScreen(playScreen);
});

// Обработчики игровых кнопок
gameButtons.forEach(button => {
  button.addEventListener('click', () => {
    const gameType = button.getAttribute('data-game');
    openGameScreen(gameType);
  });
});

// Открытие игрового экрана
function openGameScreen(gameType) {
  // Устанавливаем заголовок игры
  document.getElementById('game-title').textContent = getGameTitle(gameType);
  
  // Показываем игровой экран
  showScreen(gameScreen);
  
  // Устанавливаем обработчик для кнопки "Сделать ставку"
  document.getElementById('play-game-btn').onclick = () => playGame(gameType);
}

// Получение названия игры
function getGameTitle(gameType) {
  const gameTitles = {
    'roulette': 'Рулетка',
    'play': 'Кости',
    'russian': 'Русская рулетка',
    'jewish': 'Еврейская рулетка',
    'dice': 'Кубик',
    'slots': 'Слоты'
  };
  
  return gameTitles[gameType] || 'Игра';
}

// Игровая логика
async function playGame(gameType) {
  const betInput = document.getElementById('bet-amount');
  const betAmount = parseInt(betInput.value);
  
  if (!betAmount || betAmount <= 0) {
    alert('Пожалуйста, введите корректную ставку');
    return;
  }
  
  if (!initData) {
    console.error('Telegram WebApp initData отсутствует');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/game/${gameType}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        initData,
        bet: betAmount
      })
    });
    
    const result = await response.json();
    
    const gameResultElement = document.getElementById('game-result');
    
    if (result.success) {
      gameResultElement.textContent = `Вы выиграли ${result.winnings} LumeCoin!`;
      gameResultElement.style.color = '#2ecc71'; // Зеленый цвет для выигрыша
      
      // Обновляем баланс на главном экране
      document.getElementById('balance-amount').textContent = result.new_balance;
    } else {
      gameResultElement.textContent = result.message || 'Вы проиграли';
      gameResultElement.style.color = '#e74c3c'; // Красный цвет для проигрыша
    }
  } catch (error) {
    console.error('Ошибка при игре:', error);
    document.getElementById('game-result').textContent = 'Ошибка при выполнении запроса';
  }
}

// Кнопка обновления профиля
document.getElementById('refresh-profile').addEventListener('click', loadUserData);

// Кнопка копирования реферальной ссылки
document.getElementById('copy-referral-link').addEventListener('click', () => {
  const referralLink = document.getElementById('referral-link').textContent;
  
  navigator.clipboard.writeText(referralLink)
    .then(() => {
      alert('Ссылка скопирована в буфер обмена');
    })
    .catch(err => {
      console.error('Ошибка при копировании ссылки:', err);
    });
});

// Кнопка "Поделиться" рефералкой
document.getElementById('share-referral').addEventListener('click', () => {
  const referralLink = document.getElementById('referral-link').textContent;
  
  if (navigator.share) {
    navigator.share({
      title: 'VapeLume Kazino',
      text: 'Присоединяйся к VapeLume Kazino!',
      url: referralLink
    })
    .catch(error => console.error('Ошибка при попытке поделиться:', error));
  } else {
    // Резервный вариант для копирования ссылки
    navigator.clipboard.writeText(referralLink)
      .then(() => {
        alert('Ссылка скопирована в буфер обмена');
      })
      .catch(err => {
        console.error('Ошибка при копировании ссылки:', err);
      });
  }
});

// Обработчики покупки/аренды титулов
document.querySelectorAll('.buy-btn, .rent-btn').forEach(button => {
 button.addEventListener('click', async (e) => {
    const titleItem = e.target.closest('.title-item');
    const title = titleItem.getAttribute('data-title');
    const price = titleItem.getAttribute('data-price');
    const type = titleItem.getAttribute('data-type');
    
    if (!initData) {
      console.error('Telegram WebApp initData отсутствует');
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/title/buy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          initData,
          title,
          type
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        alert(`🎉 Вы ${type === 'permanent' ? 'купили' : 'арендовали'} титул "${title}"!`);
        loadUserData(); // Обновляем данные пользователя
      } else {
        alert(result.message || 'Ошибка при покупке титула');
      }
    } catch (error) {
      console.error('Ошибка при покупке титула:', error);
      alert('Ошибка при выполнении запроса');
    }
  });
});

// Кнопка открытия кейса
document.getElementById('open-case-btn').addEventListener('click', async () => {
  if (!initData) {
    console.error('Telegram WebApp initData отсутствует');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/case/open`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ initData })
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert(`🎁 Вы получили ${result.reward} LumeCoin!`);
      loadUserData(); // Обновляем баланс
    } else {
      alert(result.message || 'Ошибка при открытии кейса');
    }
  } catch (error) {
    console.error('Ошибка при открытии кейса:', error);
    alert('Ошибка при выполнении запроса');
  }
});

// Кнопка сжигания монет
document.getElementById('burn-coins-btn').addEventListener('click', async () => {
  const burnAmountInput = document.getElementById('burn-amount');
  const burnAmount = parseInt(burnAmountInput.value);
  
  if (!burnAmount || burnAmount <= 0) {
    alert('Пожалуйста, введите корректную сумму');
    return;
  }
  
  if (!initData) {
    console.error('Telegram WebApp initData отсутствует');
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/burn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        initData,
        amount: burnAmount
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert(`🔥 Вы сожгли ${burnAmount} монет и получили ${result.xp_gained} XP!`);
      loadUserData(); // Обновляем данные пользователя
    } else {
      alert(result.message || 'Ошибка при сжигании монет');
    }
  } catch (error) {
    console.error('Ошибка при сжигании монет:', error);
    alert('Ошибка при выполнении запроса');
  }
});

// Загружаем начальные данные при загрузке приложения
window.addEventListener('load', () => {
  if (tgUser) {
    loadUserData();
  } else {
    console.error('Пользователь не найден. Приложение должно запускаться в Telegram WebApp');
  }
});
