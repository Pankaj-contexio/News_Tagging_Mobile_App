// This script handles the functionality of downloading selected posts as a PDF file.
    // Handle "Download PDF" button click
 async function createpdf() {
    if (selectedPosts.length === 0) {
        alertPopup("Please select at least one post to download.");
        return;
    }

    // Use selectedFilters object to get filter values
    const filters = {
        country: selectedFilters.country.length > 0
            ? selectedFilters.country
                    .map(countryId => {
                        const country = countrys.find(c => c.id === countryId);
                        return country ? country.name : null; // Get the name, or null if not found
                    })
                    .filter(Boolean) // Remove any nulls if IDs don't match
                    .join(", ")
            : "None",
        sector: selectedFilters.sector.length > 0
            ? selectedFilters.sector
                    .map(sectorId => {
                        const sector = sectors.find(s => s.id === sectorId);
                        return sector ? sector.name : null; // Get the name, or null if not found
                    })
                    .filter(Boolean) // Remove any nulls if IDs don't match
                    .join(", ")
            : "None",
        publisian: selectedFilters.publisian.length > 0
            ? selectedFilters.publisian
                    .map(publisianId => {
                        const publisian = publisians.find(p => p.id === publisianId);
                        return publisian ? publisian.name : null; // Get the name, or null if not found
                    })
                    .filter(Boolean) // Remove any nulls if IDs don't match
                    .join(", ")
            : "None",
 }

    const dateRange = document.getElementById("reportrange")?.value || null;
    const searchQuery = document.getElementById('search')?.value || null;
    const projectName = document.getElementById("project-name")?.innerText || "NEWS";
    const project_id = document.getElementById("project-name")?.getAttribute("data-id") || null;
    
    // Open a blank popup immediately on user click
    const newWindow = window.open("", "_blank");
    


    // If the popup was blocked, exit early
    if (!newWindow) {
        alertPopup("Popup blocked! Please allow popups and try again.");
        return;
    }

    // Show loading message in new window (optional)
    newWindow.document.write("<p>Loading PDF preview...</p>");
    try{
        // Now fetch the actual data
        const response = await fetch("/api/news/view-pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                post_ids: selectedPosts,
                filters,
                dateRange,
                searchQuery,
                projectName,
                project_id,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            alertPopup("Failed to download PDF: " + error.message);
            newWindow.close();  // Optional: close the blank popup
            return;
        }
        const data = await response.json();
        const pdfData = data.pdf_html;

        // Replace the loading content with the actual HTML
        newWindow.document.open();
        newWindow.document.write(pdfData);
        newWindow.document.write(`<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <script>
                document.getElementById("download-pdf-btn").addEventListener("click", async () => {
                    const downloadbutton = document.getElementById("download-pdf-btn");
                    downloadbutton.style.display = "none"; // Hide the button after clicking
                    const htmlContent = document.documentElement.outerHTML;
                    const filename = "${projectName}.pdf";
                    try {
                        const response = await fetch("/api/news/download-pdf", {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ pdf_html: htmlContent,
                                filename: filename,
                            })
                        });

                        if (!response.ok) {
                            const error = await response.json();
                            alertPopup("Failed to download PDF: " + error.message);
                            return;
                        }

                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = "${projectName}.pdf";
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    } catch (error) {
                        console.error("Error downloading PDF:", error);
                    }
                    });
            </script>
`)
        newWindow.document.title = projectName;
        newWindow.document.close();
    } catch (error) {
        console.error("Error downloading PDF:", error);
    }
};


//
//document.getElementById("download-pdf-btn").addEventListener("click", async () => {
//        if (selectedPosts.length === 0) {
//            alertPopup("Please select at least one post to download.");
//            return;
//        }
//
//        // Use selectedFilters object to get filter values
//        const filters = {
//                country: selectedFilters.country.length > 0
//                    ? selectedFilters.country
//                            .map(countryId => {
//                                const country = countrys.find(c => c.id === countryId);
//                                return country ? country.name : null; // Get the name, or null if not found
//                            })
//                            .filter(Boolean) // Remove any nulls if IDs don't match
//                            .join(", ")
//                    : "None",
//                sector: selectedFilters.sector.length > 0
//                    ? selectedFilters.sector
//                            .map(sectorId => {
//                                const sector = sectors.find(s => s.id === sectorId);
//                                return sector ? sector.name : null; // Get the name, or null if not found
//                            })
//                            .filter(Boolean) // Remove any nulls if IDs don't match
//                            .join(", ")
//                    : "None",
//                publisian: selectedFilters.publisian.length > 0
//                    ? selectedFilters.publisian
//                            .map(publisianId => {
//                                const publisian = publisians.find(p => p.id === publisianId);
//                                return publisian ? publisian.name : null; // Get the name, or null if not found
//                            })
//                            .filter(Boolean) // Remove any nulls if IDs don't match
//                            .join(", ")
//                    : "None",
//        }
//
//
//        const dateRange = document.getElementById("reportrange")?.innerText || null;
//        const searchQuery = document.getElementById('search')?.value || null;
//        const projectName = document.getElementById("project-name")?.innerText || "SocialMedia";
//        const project_id = document.getElementById("project-name")?.getAttribute("data-id") || null;
//        console.log("Project Name:", projectName);
//        // Send data to the backend
//        try {
//            const response = await fetch("/api/news/view-pdf", {
//                method: "POST",
//                headers: { "Content-Type": "application/json" },
//                body: JSON.stringify({
//                    post_ids: selectedPosts,
//                    filters,
//                    dateRange,
//                    searchQuery,
//                    projectName,
//                    project_id,
//                }),
//            });
//
//            if (!response.ok) {
//                const error = await response.json();
//                alertPopup("Failed to download PDF: " + error.message);
//                return;
//            }
//
//            const blob = await response.blob();
//            const url = window.URL.createObjectURL(blob);
//            const a = document.createElement("a");
//            a.href = url;
//            a.download = "selected_posts.pdf";
//            document.body.appendChild(a);
//            a.click();
//            a.remove();
//        } catch (error) {
//            console.error("Error downloading PDF:", error);
//        }
//    });


async function generateReport(endpoint, filename) {
    if (selectedPosts.length === 0) {
        alertPopup("Please select at least one post to download.");
        return;
    }

    // Use selectedFilters object to get filter values
    const filters = {
            country: selectedFilters.country.length > 0
                ? selectedFilters.country
                        .map(countryId => {
                            const country = countrys.find(c => c.id === countryId);
                            return country ? country.name : null; // Get the name, or null if not found
                        })
                        .filter(Boolean) // Remove any nulls if IDs don't match
                        .join(", ")
                : "None",
            sector: selectedFilters.sector.length > 0
                ? selectedFilters.sector
                        .map(sectorId => {
                            const sector = sectors.find(s => s.id === sectorId);
                            return sector ? sector.name : null; // Get the name, or null if not found
                        })
                        .filter(Boolean) // Remove any nulls if IDs don't match
                        .join(", ")
                : "None",
            publisian: selectedFilters.publisian.length > 0
                ? selectedFilters.publisian
                        .map(publisianId => {
                            const publisian = publisians.find(p => p.id === publisianId);
                            return publisian ? publisian.name : null; // Get the name, or null if not found
                        })
                        .filter(Boolean) // Remove any nulls if IDs don't match
                        .join(", ")
                : "None",
            site: selectedFilters.site.length > 0
                    ? selectedFilters.site
                          .map(siteId => {
                              const site = sites.find(s => s.id === siteId);
                              return site ? site.name : null; // Get the name, or null if not found
                          })
                          .filter(Boolean) // Remove any nulls if IDs don't match
                          .join(", ")
                    : "None",
                person: selectedFilters.person.length > 0
                    ? selectedFilters.person
                          .map(personId => {
                              const person = persons.find(p => p.id === personId);
                              return person ? person.name : null; // Get the name, or null if not found
                          })
                          .filter(Boolean) // Remove any nulls if IDs don't match
                          .join(", ")
                    : "None",
    };


    const dateRange = document.getElementById("reportrange")?.innerText || null;
    const searchQuery = document.getElementById('search')?.value || null;
    const projectName = document.getElementById("project-name")?.innerText || "Report";
    const project_id = document.getElementById("project-name")?.getAttribute("data-id") || null;

    document.getElementById("download_loder").style.display = "flex";

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                post_ids: selectedPosts,
                filters,
                dateRange,
                searchQuery,
                projectName,
                project_id,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            alertPopup(`Failed to download: ${error.message}`);
            return;
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (error) {
        console.error("Error:", error);
        alertPopup("An unexpected error occurred");
    }

    document.getElementById("download_loder").style.display = "none";
}


// PDF Button
document.getElementById("download-pdf-btn").addEventListener("click", () => {
    generateReport("/api/download-pdf", "selected_posts.pdf");
});

// DOC Button
document.getElementById("download-doc-btn").addEventListener("click", () => {
    generateReport("/api/download-doc", "selected_posts.docx");
});
