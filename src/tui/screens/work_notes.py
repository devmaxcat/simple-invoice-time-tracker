class WorkNotesScreen:
    def __init__(self):
        self.notes = ""

    def display(self):
        print("Work Notes:")
        print("Enter your notes below (press Enter to save):")
        print(self.notes)

    def input_notes(self):
        self.notes = input("Notes: ")

    def save_notes(self):
        # Logic to save notes can be implemented here
        print("Notes saved.")