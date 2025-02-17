document.getElementById('add-event-button').addEventListener('click', async () => {
    // Получаем данные из полей ввода
    const date = document.getElementById('event-date').value;
    const startTime = document.getElementById('event-start-time').value;
    const endTime = document.getElementById('event-end-time').value;
    const description = document.getElementById('event-description').value;

    // Проверяем, что все поля заполнены
    if (!date || !startTime || !endTime || !description) {
        alert('Пожалуйста, заполните все поля.');
        return;
    }

    // Формируем объект с данными события
    const eventData = {
        date: date,
        start_time: startTime,
        end_time: endTime,
        description: description
    };

    try {
        // Отправляем данные боту через Telegram Bot API
        const botToken = 'YOUR_BOT_TOKEN'; // Замените на токен вашего бота
        const chatId = Telegram.WebApp.initDataUnsafe.user.id; // ID пользователя

        const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: chatId,
                text: JSON.stringify(eventData) // Преобразуем данные в JSON
            })
        });

        if (!response.ok) {
            console.error('Ошибка при отправке данных боту:', response.statusText);
        } else {
            alert('Событие успешно добавлено!');
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
});