
async function updatepartyrating(cardid, countryId) {
    const card = document.getElementById(cardid);
    const addRate = card.querySelector('.rate-party').value;
    const removeRate = card.querySelector('.remove-rate-party').value;
    let partyRating = card.querySelector('.party_rating').value;
    let removePartyRating = card.querySelector('.remove-party_rating').value;

    if (!addRate || !removeRate || !partyRating || !removePartyRating) {
        alertPopup("Please fill all fields");
        return;
    }
    // if (removeRate !== 'All') {
    //     removePartyRating = partyRating;
    //     card.querySelector('.remove-party_rating').value = removePartyRating;
    // }
    const data = {
        addRate: addRate,
        removeRate: removeRate,
        partyRating: partyRating,
        removePartyRating: removePartyRating,
        countryId: countryId
    };
    try {
        const response = await fetch('/api/analytics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            alertPopup(result.message);
            // Optionally, you can refresh the page or update the UI
           
        } else {
            const error = await response.json();
            alertPopup(error.message || "An error occurred while updating ratings.");
        }
    } catch (error) {
        console.error("Error:", error);
        alertPopup("An unexpected error occurred.");
    }


}


async function updateForeignRelation(cardid) {
    const card = document.getElementById(cardid);
    const countryRelation = card.querySelector('.country-relation').value;
    const rateCountry = card.querySelector('.rate-country').value;
    const countryRating = card.querySelector('.country_rating').value;

    if (!countryRelation || !rateCountry || !countryRating) {
        alertPopup("Please fill all fields");
        return;
    }

    const data = {
        countryRelation: countryRelation,
        rateCountry: rateCountry,
        countryRating: countryRating
    };

    try {
        const response = await fetch('/api/relations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            alertPopup(result.message);
            // Optionally, you can refresh the page or update the UI
            
        } else {
            const error = await response.json();
            alertPopup(error.message || "An error occurred while updating foreign relations.");
        }
    } catch (error) {
        console.error("Error:", error);
        alertPopup("An unexpected error occurred.");
    }
}



