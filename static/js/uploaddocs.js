const loader = document.getElementById('fetch-loader');
async function uploaddocuments(){
    loader.style.display = "block";
    const urlParams = new URLSearchParams(window.location.search);    
    const project_id = urlParams.get('project_id');
    const adddocs = document.getElementById("add-document");
    document.getElementById("document_project_id_input").value = project_id;
    const descriptionInput = document.getElementById('documentDescriptionInput');
    descriptionInput.value = ""; // Clear the description input
    const docInput = document.getElementById('documentInput');
    docInput.value = ""; // Clear the file input
    adddocs.style.display = "block";
    const documentresponse = await fetch(`/api/document/list-documents/${project_id}`, {
        method: 'GET',})
    const data = await documentresponse.json();
    if (!documentresponse.ok) {
        alertPopup(data.error || 'Failed to fetch documents');
        loader.style.display = "none";
        return;
    }
    const table = document.querySelector("#reports-table tbody");
    table.innerHTML = ""; // Clear existing rows
    data.forEach(doc => {
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td>${doc.file_name}</td>
            <td>${doc.description}</td>
            <td style="padding: 5px;">
                <a href="/api/document/download/${project_id}/${doc.file_name}" target="_blank" class="btn btn-sm btn-success" style="margin:0px;">Download</a>
                <button class="delete-button btn btn-danger btn-sm" onclick="deleteDocument('${doc.file_name}', '${doc.path}', '${project_id}', '${doc.description}')"
                style="background-color:#c82333; border-color:#bd2130 font-size:12px; margin:0px; line-height: 1;"><i class="fa fa-trash-o" style="margin-right: 2px;"></i>Delete</button>
            </td>
        `;
        table.appendChild(newRow);
    });
    loader.style.display = "none";
    
}

document.getElementById('uploadDocumentButton').addEventListener('click', async function () {
    
    const docInput = document.getElementById('documentInput');
    const project_id = document.getElementById("document_project_id_input").value;
    const descriptionInput = document.getElementById('documentDescriptionInput').value;


    const file = docInput.files[0];
    const table = document.querySelector("#reports-table tbody");
    if (!file) {
        alertPopup("Please select a file");
        return;
    }

    const formData = new FormData();
    formData.append('doc', file);
    formData.append('project_id', project_id);
    formData.append('description', descriptionInput);
    loader.style.display = "block";
    try {
        const response = await fetch('/api/document/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            const adddoc = document.getElementById("add-document");
            adddoc.style.display = "none";
            loader.style.display = "none";
            alertPopup(data.error || 'Upload failed');
            
            return;
        }
        loader.style.display = "none";
        const fileName = data.file_name;
        const documenturl = data.file_url;
        const description = data.file_description;
        // Create the <li> element
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td>${fileName}</td>
            <td>${description}</td>
            <td style="padding: 5px;">
                <a href="/api/document/download/${project_id}/${fileName}" target="_blank" class="btn btn-sm btn-success" style="margin:0px;">Download</a>
                <button class="delete-button btn btn-danger" onclick="deleteDocument('${fileName}', '${documenturl}', '${project_id}', '${description}')"
                style="background-color:#c82333; border-color:#bd2130 font-size:12px; margin:0px; line-height: 1;"><i class="fa fa-trash-o" style="margin-right: 2px;"></i>Delete</button>
            </td>
        `;
        

        table.appendChild(newRow);
        // const adddoc = document.getElementById("add-document");
        // adddoc.style.display = "none";
        
        alertPopup("Document uploaded successfully");
        docInput.value = ""; // Clear the file input
        document.getElementById('documentDescriptionInput').value = ""; // Clear the description input
        
        const uploadBoxText = document.getElementById('upload-box-text');
        const fileNameDisplay = document.getElementById('file-name-display');
        fileNameDisplay.textContent = '';
        fileNameDisplay.style.display = 'none';
        uploadBoxText.textContent = 'Drop files here or click to upload';
        uploadBoxText.style.display = 'block';

    } catch (error) {
        console.error('Upload failed:', error);
        loader.style.display = "none";
        alertPopup("Error uploading document.");
    }
});

async function deleteDocument(fileName, fileurl, project_id, description) {
    const confirmDelete = await confirmWithCustomPopup("Are you sure you want to delete this Document?");
    if (!confirmDelete) return;
    loader.style.display = "block";
    fetch('/api/document/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            file_name: fileName, 
            file_url: fileurl, 
            project_id: project_id, 
            file_description: description 
        })
    })
    .then(response => response.json())
    .then(data => {
        
        const table = document.querySelector("#reports-table tbody");
        const cells = table.querySelectorAll('td');
        let fileNametag = null;

        cells.forEach(cell => {
            if (cell.textContent.includes(fileName)) {
                fileNametag = cell;
            }
        });
        
        if (!fileNametag) {
            alertPopup("Document not found in the table.");
            return;
        }
        const filetr = fileNametag.closest('tr');
        console.log(filetr);
        if (filetr) {
            table.removeChild(filetr);
        }
        loader.style.display = "none";
        alertPopup(data.message || 'Document deleted successfully');
    })
    .catch(error => {
        console.error('Error deleting document:', error);
        alertPopup("Error deleting document.");
    });
}




const fileInput = document.getElementById('documentInput');
const uploadBoxText = document.getElementById('upload-box-text');
const fileNameDisplay = document.getElementById('file-name-display');

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    const name = fileInput.files[0].name;
    fileNameDisplay.textContent = name;
    fileNameDisplay.style.display = 'block';
    uploadBoxText.style.display = 'none';
  } else {
    fileNameDisplay.textContent = '';
    fileNameDisplay.style.display = 'none';
    uploadBoxText.textContent = 'Drop files here or click to upload';
    uploadBoxText.style.display = 'block';
  }
});