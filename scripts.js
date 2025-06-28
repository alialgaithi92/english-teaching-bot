// Add interactivity to the dashboard or forms

document.addEventListener("DOMContentLoaded", () => {
    // Handle showing/hiding options field based on question type
    const questionTypeField = document.getElementById("question_type");
    const optionsField = document.getElementById("options");

    if (questionTypeField && optionsField) {
        // Show or hide the options field based on the selected question type
        questionTypeField.addEventListener("change", (event) => {
            const selectedType = event.target.value;

            if (selectedType === "multiple_choice") {
                optionsField.parentElement.style.display = "block"; // Show options field
            } else {
                optionsField.parentElement.style.display = "none"; // Hide options field
                optionsField.value = ""; // Clear the options field value
            }
        });

        // Trigger the change event to apply the correct initial state
        questionTypeField.dispatchEvent(new Event("change"));
    }

    // Confirmation dialog for deleting a question
    const deleteLinks = document.querySelectorAll("a[href*='/delete_question/']");

    deleteLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            const confirmed = confirm("Are you sure you want to delete this question?");
            if (!confirmed) {
                event.preventDefault(); // Prevent navigation if not confirmed
            }
        });
    });
});
