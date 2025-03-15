import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
from insightface.app import FaceAnalysis
import os


class FaceSwapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Swap Application")
        self.root.geometry("1200x800")

        # Initialize InsightFace
        self.face_analyzer = FaceAnalysis()
        self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))

        # Variables
        self.source_image = None  # Face image
        self.target_image = None  # Image with humans
        self.source_tk_image = None
        self.target_tk_image = None
        self.result_image = None

        self.source_faces = []
        self.target_faces = []
        self.selected_face_indices = []

        self.is_cropping_source = False
        self.is_cropping_target = False
        self.crop_start_x = 0
        self.crop_start_y = 0
        self.crop_rect = None

        # Create UI
        self.create_ui()

    def create_ui(self):
        # Main frames
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top buttons
        ttk.Button(
            top_frame, text="Load Source Face", command=self.load_source_image
        ).grid(row=0, column=0, padx=5)
        ttk.Button(top_frame, text="Crop Source", command=self.start_crop_source).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(
            top_frame, text="Load Target Image", command=self.load_target_image
        ).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Crop Target", command=self.start_crop_target).grid(
            row=0, column=3, padx=5
        )
        ttk.Button(top_frame, text="Detect Faces", command=self.detect_faces).grid(
            row=0, column=4, padx=5
        )
        ttk.Button(top_frame, text="Swap Faces", command=self.swap_faces).grid(
            row=0, column=5, padx=5
        )
        ttk.Button(top_frame, text="Save Result", command=self.save_result).grid(
            row=0, column=6, padx=5
        )

        # Image canvases
        left_frame = ttk.LabelFrame(main_frame, text="Source Face")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        right_frame = ttk.LabelFrame(main_frame, text="Target Image")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.source_canvas = tk.Canvas(left_frame, bg="light gray")
        self.source_canvas.pack(fill=tk.BOTH, expand=True)

        self.target_canvas = tk.Canvas(right_frame, bg="light gray")
        self.target_canvas.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind events
        self.source_canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.source_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.source_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.target_canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.target_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.target_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.root.bind("<Configure>", self.on_window_resize)

    def on_window_resize(self, event=None):
        if hasattr(self, "source_canvas") and hasattr(self, "target_canvas"):
            if self.source_image is not None:
                self.display_source_image()
            if self.target_image is not None:
                self.display_target_image()

    def load_source_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            try:
                self.source_image = cv2.imread(file_path)
                self.source_image = cv2.cvtColor(self.source_image, cv2.COLOR_BGR2RGB)
                self.display_source_image()
                self.source_faces = []  # Reset face detection
                self.status_var.set(
                    f"Source face image loaded: {os.path.basename(file_path)}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def load_target_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            try:
                self.target_image = cv2.imread(file_path)
                self.target_image = cv2.cvtColor(self.target_image, cv2.COLOR_BGR2RGB)
                self.display_target_image()
                self.target_faces = []  # Reset face detection
                self.selected_face_indices = []  # Reset selections
                self.status_var.set(
                    f"Target image loaded: {os.path.basename(file_path)}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def display_source_image(self):
        if self.source_image is None:
            return

        canvas_width = self.source_canvas.winfo_width()
        canvas_height = self.source_canvas.winfo_height()

        if canvas_width <= 1:  # Canvas not realized yet
            canvas_width = 400
            canvas_height = 400

        # Resize image to fit canvas
        img_height, img_width = self.source_image.shape[:2]
        scale = min(canvas_width / img_width, canvas_height / img_height)

        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        resized_image = cv2.resize(self.source_image, (new_width, new_height))
        self.source_tk_image = ImageTk.PhotoImage(image=Image.fromarray(resized_image))

        # Clear and display image
        self.source_canvas.delete("all")
        self.source_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.source_tk_image,
            anchor=tk.CENTER,
        )

        # Draw faces if detected
        if self.source_faces:
            self.draw_source_faces()

    def display_target_image(self):
        if self.target_image is None:
            return

        canvas_width = self.target_canvas.winfo_width()
        canvas_height = self.target_canvas.winfo_height()

        if canvas_width <= 1:  # Canvas not realized yet
            canvas_width = 400
            canvas_height = 400

        # Resize image to fit canvas
        img_height, img_width = self.target_image.shape[:2]
        scale = min(canvas_width / img_width, canvas_height / img_height)

        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        resized_image = cv2.resize(self.target_image, (new_width, new_height))
        self.target_tk_image = ImageTk.PhotoImage(image=Image.fromarray(resized_image))

        # Clear and display image
        self.target_canvas.delete("all")
        self.target_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.target_tk_image,
            anchor=tk.CENTER,
        )

        # Draw faces if detected
        if self.target_faces:
            self.draw_target_faces()

    def start_crop_source(self):
        if self.source_image is not None:
            self.is_cropping_source = True
            self.is_cropping_target = False
            self.status_var.set("Click and drag to crop source image")

    def start_crop_target(self):
        if self.target_image is not None:
            self.is_cropping_source = False
            self.is_cropping_target = True
            self.status_var.set("Click and drag to crop target image")

    def on_canvas_click(self, event):
        canvas = event.widget

        if (canvas == self.source_canvas and self.is_cropping_source) or (
            canvas == self.target_canvas and self.is_cropping_target
        ):
            # Start cropping
            self.crop_start_x = event.x
            self.crop_start_y = event.y

            # Create crop rectangle
            if self.crop_rect:
                canvas.delete(self.crop_rect)

            self.crop_rect = canvas.create_rectangle(
                self.crop_start_x,
                self.crop_start_y,
                self.crop_start_x,
                self.crop_start_y,
                outline="yellow",
                width=2,
            )
        elif (
            canvas == self.target_canvas
            and not self.is_cropping_target
            and self.target_faces
        ):
            # Face selection in target image
            self.toggle_face_selection(event.x, event.y)

    def on_canvas_drag(self, event):
        canvas = event.widget

        if (canvas == self.source_canvas and self.is_cropping_source) or (
            canvas == self.target_canvas and self.is_cropping_target
        ):
            if self.crop_rect:
                canvas.coords(
                    self.crop_rect,
                    self.crop_start_x,
                    self.crop_start_y,
                    event.x,
                    event.y,
                )

    def on_canvas_release(self, event):
        canvas = event.widget

        if (canvas == self.source_canvas and self.is_cropping_source) or (
            canvas == self.target_canvas and self.is_cropping_target
        ):
            if self.crop_rect:
                x1, y1, x2, y2 = canvas.coords(self.crop_rect)

                # Ensure correct order
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1

                # Convert canvas coordinates to image coordinates
                if canvas == self.source_canvas:
                    self.crop_image(
                        self.source_image,
                        self.source_canvas,
                        x1,
                        y1,
                        x2,
                        y2,
                        is_source=True,
                    )
                    self.is_cropping_source = False
                else:
                    self.crop_image(
                        self.target_image,
                        self.target_canvas,
                        x1,
                        y1,
                        x2,
                        y2,
                        is_source=False,
                    )
                    self.is_cropping_target = False

                canvas.delete(self.crop_rect)
                self.crop_rect = None
                self.status_var.set("Image cropped")

    def crop_image(self, image, canvas, x1, y1, x2, y2, is_source):
        # Get canvas and image dimensions
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        img_height, img_width = image.shape[:2]

        # Calculate scale and offset
        scale = min(canvas_width / img_width, canvas_height / img_height)

        # Calculate offset for centering
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        offset_x = (canvas_width - scaled_width) / 2
        offset_y = (canvas_height - scaled_height) / 2

        # Convert canvas coordinates to image coordinates
        img_x1 = max(0, int((x1 - offset_x) / scale))
        img_y1 = max(0, int((y1 - offset_y) / scale))
        img_x2 = min(img_width, int((x2 - offset_x) / scale))
        img_y2 = min(img_height, int((y2 - offset_y) / scale))

        # Ensure we have a valid crop area
        if img_x1 >= img_x2 or img_y1 >= img_y2:
            messagebox.showerror("Error", "Invalid crop area")
            return

        # Crop the image
        cropped = image[img_y1:img_y2, img_x1:img_x2]

        if is_source:
            self.source_image = cropped
            self.display_source_image()
            self.source_faces = []  # Reset face detection
        else:
            self.target_image = cropped
            self.display_target_image()
            self.target_faces = []  # Reset face detection
            self.selected_face_indices = []  # Reset selections

    def detect_faces(self):
        if self.source_image is None or self.target_image is None:
            messagebox.showerror("Error", "Please load both source and target images")
            return

        try:
            # Detect faces in source image
            self.source_faces = self.face_analyzer.get(self.source_image)

            # Detect faces in target image
            self.target_faces = self.face_analyzer.get(self.target_image)

            # Reset selections
            self.selected_face_indices = []

            # Display images with face boxes
            self.display_source_image()
            self.display_target_image()

            if not self.source_faces:
                messagebox.showwarning("Warning", "No faces detected in source image")

            if not self.target_faces:
                messagebox.showwarning("Warning", "No faces detected in target image")
            else:
                self.status_var.set(
                    f"Detected {len(self.target_faces)} faces in target image. Click on faces to select for swapping."
                )

        except Exception as e:
            messagebox.showerror("Error", f"Face detection failed: {str(e)}")

    def draw_source_faces(self):
        if not self.source_faces:
            return

        if self.source_image is None:
            messagebox.showerror("Error", "No source image to draw faces")
            return

        # Get canvas dimensions
        canvas_width = self.source_canvas.winfo_width()
        canvas_height = self.source_canvas.winfo_height()

        # Get image dimensions
        img_height, img_width = self.source_image.shape[:2]

        # Calculate scale and offset
        scale = min(canvas_width / img_width, canvas_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        offset_x = (canvas_width - scaled_width) / 2
        offset_y = (canvas_height - scaled_height) / 2

        # Draw rectangles for each face
        for face in self.source_faces:
            bbox = face.bbox.astype(int)

            # Convert to canvas coordinates
            x1 = int(bbox[0] * scale + offset_x)
            y1 = int(bbox[1] * scale + offset_y)
            x2 = int(bbox[2] * scale + offset_x)
            y2 = int(bbox[3] * scale + offset_y)

            # Draw rectangle
            self.source_canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=2)

    def draw_target_faces(self):
        if not self.target_faces:
            return

        if self.target_image is None:
            messagebox.showerror("Error", "No target image to draw faces")
            return

        # Get canvas dimensions
        canvas_width = self.target_canvas.winfo_width()
        canvas_height = self.target_canvas.winfo_height()

        # Get image dimensions
        img_height, img_width = self.target_image.shape[:2]

        # Calculate scale and offset
        scale = min(canvas_width / img_width, canvas_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        offset_x = (canvas_width - scaled_width) / 2
        offset_y = (canvas_height - scaled_height) / 2

        # Draw rectangles for each face
        for i, face in enumerate(self.target_faces):
            bbox = face.bbox.astype(int)

            # Convert to canvas coordinates
            x1 = int(bbox[0] * scale + offset_x)
            y1 = int(bbox[1] * scale + offset_y)
            x2 = int(bbox[2] * scale + offset_x)
            y2 = int(bbox[3] * scale + offset_y)

            # Draw rectangle with different color if selected
            color = "red" if i in self.selected_face_indices else "green"
            width = 3 if i in self.selected_face_indices else 2

            self.target_canvas.create_rectangle(
                x1, y1, x2, y2, outline=color, width=width
            )

            # Display index number for easier reference
            self.target_canvas.create_text(
                (x1 + x2) // 2,
                y1 - 10,
                text=str(i + 1),
                fill=color,
                font=("Arial", 12, "bold"),
            )

    def toggle_face_selection(self, x, y):
        if self.target_image is None:
            messagebox.showerror("Error", "No target image to select faces")
            return

        # Get canvas dimensions
        canvas_width = self.target_canvas.winfo_width()
        canvas_height = self.target_canvas.winfo_height()

        # Get image dimensions
        img_height, img_width = self.target_image.shape[:2]

        # Calculate scale and offset
        scale = min(canvas_width / img_width, canvas_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        offset_x = (canvas_width - scaled_width) / 2
        offset_y = (canvas_height - scaled_height) / 2

        # Convert canvas coordinates to image coordinates
        img_x = int((x - offset_x) / scale)
        img_y = int((y - offset_y) / scale)

        # Check if click is inside any face bounding box
        for i, face in enumerate(self.target_faces):
            bbox = face.bbox.astype(int)

            if bbox[0] <= img_x <= bbox[2] and bbox[1] <= img_y <= bbox[3]:
                # Toggle selection
                if i in self.selected_face_indices:
                    self.selected_face_indices.remove(i)
                    self.status_var.set(f"Face {i + 1} deselected")
                else:
                    self.selected_face_indices.append(i)
                    self.status_var.set(f"Face {i + 1} selected")

                # Redraw faces
                self.display_target_image()
                break

    def swap_faces(self):
        if not self.source_faces:
            messagebox.showerror("Error", "No face detected in source image")
            return

        if not self.target_faces:
            messagebox.showerror("Error", "No faces detected in target image")
            return

        if not self.selected_face_indices:
            messagebox.showerror("Error", "Please select at least one face to swap")
            return

        if self.target_image is None:
            messagebox.showerror("Error", "No target image to swap faces")
            return

        if self.source_image is None:
            messagebox.showerror("Error", "No source image to swap faces")
            return

        try:
            # Use the first face from source image
            source_face = self.source_faces[0]

            # Create a copy of target image for the result
            self.result_image = self.target_image.copy()

            # Process each selected face
            for idx in self.selected_face_indices:
                if idx >= len(self.target_faces):
                    continue

                target_face = self.target_faces[idx]

                # Get bounding boxes
                src_bbox = source_face.bbox.astype(int)
                dst_bbox = target_face.bbox.astype(int)

                # Extract source face
                src_face = self.source_image[
                    src_bbox[1] : src_bbox[3], src_bbox[0] : src_bbox[2]
                ]

                # Calculate dimensions for target face
                dst_width = dst_bbox[2] - dst_bbox[0]
                dst_height = dst_bbox[3] - dst_bbox[1]

                # Resize source face to match target face dimensions
                src_face_resized = cv2.resize(src_face, (dst_width, dst_height))

                # Create a mask for blending
                mask = np.zeros((dst_height, dst_width), dtype=np.uint8)
                center = (dst_width // 2, dst_height // 2)
                axes = (
                    dst_width // 2 - 5,
                    dst_height // 2 - 5,
                )  # Slightly smaller than face
                cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)  # type: ignore

                # Blur the mask for smoother blending
                mask = cv2.GaussianBlur(mask, (19, 19), 11)

                # Convert to 3-channel mask
                mask_3channel = np.stack([mask] * 3, axis=2) / 255.0

                # Get target face region
                target_region = self.result_image[
                    dst_bbox[1] : dst_bbox[3], dst_bbox[0] : dst_bbox[2]
                ]

                # Blend the faces
                blended = (src_face_resized * mask_3channel) + (
                    target_region * (1 - mask_3channel)
                )

                # Replace in the result image
                self.result_image[
                    dst_bbox[1] : dst_bbox[3], dst_bbox[0] : dst_bbox[2]
                ] = blended.astype(np.uint8)

            # Display the result
            self.target_image = self.result_image
            self.display_target_image()
            self.status_var.set("Face swap completed!")

        except Exception as e:
            messagebox.showerror("Error", f"Face swap failed: {str(e)}")

    def save_result(self):
        if self.result_image is None:
            messagebox.showerror("Error", "No result to save")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*"),
            ],
        )

        if file_path:
            cv2.imwrite(file_path, cv2.cvtColor(self.result_image, cv2.COLOR_RGB2BGR))
            self.status_var.set(f"Result saved to {file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceSwapApp(root)
    root.mainloop()
