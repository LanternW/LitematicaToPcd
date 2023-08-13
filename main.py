import numpy as np
from glumpy import app, gl, glm, gloo
from extract_nbt import converter


def cubes(centers, size):
    vtype = [('a_position', np.float32, 3), ('a_oricolor', np.float32),
             ('a_normal',   np.float32, 3), ('a_color',    np.float32, 4)]
    itype = np.uint32

    # Face Normals
    n = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0],
                  [-1, 0, 1], [0, -1, 0], [0, 0, -1]])
    
    # Vertice colors
    c = np.array([[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1],
                  [0.5, 0.5, 0, 1], [0.5, 0.5, 0, 1], [0.5, 0.5, 0, 1], [0.5, 0.5, 0, 1] ])
    
    faces_p = [0, 1, 2, 3,  0, 3, 4, 5,   0, 5, 6, 1,
               1, 6, 7, 2,  7, 4, 3, 2,   4, 7, 6, 5]
    faces_c = [0, 1, 2, 3,  0, 3, 4, 5,   0, 5, 6, 1,
               1, 6, 7, 2,  7, 4, 3, 2,   4, 7, 6, 5]
    faces_n = [0, 0, 0, 0,  1, 1, 1, 1,   2, 2, 2, 2,
               3, 3, 3, 3,  4, 4, 4, 4,   5, 5, 5, 5]
    

    vertex_count    = len(centers)
    vertices_length = 24 * vertex_count + 6
    vertices       = np.zeros(vertices_length, vtype)

    vertices_a_position  = []
    vertices_a_normal    = []
    vertices_a_color     = []
    vertices_a_ori_color = []

    filled = np.resize(
       np.array([0, 1, 2, 0, 2, 3], dtype=itype), vertex_count * 6 * (2 * 3))
    filled += np.repeat(4 * np.arange(vertex_count*6, dtype=itype), 6)

    outline = np.resize(
        np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=itype), vertex_count * 6 * (2 * 4))
    outline += np.repeat(4 * np.arange(vertex_count*6, dtype=itype), 8)

    size_2 = size/2
    for center in centers:
        center_np = np.array(center)
        # Vertices positions
        p = np.array([[1, 1, 1]  , [-1, 1, 1], [-1, -1, 1], [1, -1, 1],
                      [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, -1]], dtype=float) * size_2 + center_np
        
        vertices_a_position.extend(p[faces_p])
        vertices_a_normal.extend(n[faces_n])
        vertices_a_color.extend(c[faces_c])
    
    ori    = np.array([0,0,0],  dtype=np.float32)
    axis_x = np.array([100,0,0], dtype=np.float32)
    axis_y = np.array([0,100,0], dtype=np.float32)
    axis_z = np.array([0,0,100], dtype=np.float32)

    color_r = np.array([1,0,0,1], dtype=np.float32)
    color_g = np.array([0,1,0,1], dtype=np.float32)
    color_b = np.array([0,0,1,1], dtype=np.float32)

    axis_coords          = [ori, axis_x, ori, axis_y, ori, axis_z ]
    vertices_a_position.extend(axis_coords)
    vertices_a_normal.extend(axis_coords)

    axis_colors          = [color_r, color_r, color_g, color_g, color_b, color_b ]
    vertices_a_color.extend(axis_colors)

    vertices['a_position'] = np.array(vertices_a_position , dtype=np.float32)
    vertices['a_normal']   = np.array(vertices_a_normal   , dtype=np.float32)
    vertices['a_color']    = np.array(vertices_a_color    , dtype=np.float32)

    vertices_a_ori_color.extend([np.array(0.0, dtype=np.float32) for _ in range(24 * vertex_count)])
    vertices_a_ori_color.extend([np.array(1.0, dtype=np.float32) for _ in range(6)])
    vertices['a_oricolor']    = np.array(vertices_a_ori_color    , dtype=np.float32)

    
    vertices = vertices.view(gloo.VertexBuffer)
    filled   = filled.view(gloo.IndexBuffer)
    outline  = outline.view(gloo.IndexBuffer)


    axis_outline = np.resize( np.array([1,2,3,4,5,6], dtype=itype) + np.array([24*len(centers)-1 for _ in range(6)] , dtype=itype) , 6 )
    axis_outline = axis_outline.view(gloo.IndexBuffer)

    return vertices, filled, outline, axis_outline


vertex = """
uniform mat4   u_model;         // Model matrix
uniform mat4   u_view;          // View matrix
uniform mat4   u_projection;    // Projection matrix
attribute vec4 a_color;         // Vertex color
attribute vec3 a_position;      // Vertex position
attribute vec3 a_normal;        // Vertex normal
attribute float  a_oricolor;      // Vertex oricolor

varying vec4   v_color;         // Interpolated fragment color (out)
varying vec3   v_normal;        // Interpolated normal (out)
varying vec3   v_position;      // Interpolated position (out)
varying float    ori_color;

void main()
{
    // Assign varying variables
    v_color    = a_color;      
    v_normal   = a_normal;
    v_position = a_position;
    ori_color  = a_oricolor;

    // Final position
    gl_Position = u_projection * u_view * u_model * vec4(a_position,1.0);
}
"""

fragment = """
uniform mat4      u_model;           // Model matrix
uniform mat4      u_view;            // View matrix
uniform mat4      u_normal;          // Normal matrix
uniform mat4      u_projection;      // Projection matrix
uniform vec4      u_color;           // Global color
uniform vec3      u_light_position;  // Light position
uniform vec3      u_light_intensity; // Light intensity

varying float      ori_color;
varying vec4      v_color;           // Interpolated fragment color (in)
varying vec3      v_normal;          // Interpolated normal (in)
varying vec3      v_position;        // Interpolated position (in)
void main()
{
    // Calculate normal in world coordinates
    vec3 normal = normalize(u_normal * vec4(v_normal,1.0)).xyz;

    // Calculate the location of this fragment (pixel) in world coordinates
    vec3 position = vec3(u_view*u_model * vec4(v_position, 1));

    // Calculate the vector from this pixels surface to the light source
    vec3 surfaceToLight = u_light_position - position;

    // Calculate the cosine of the angle of incidence (brightness)
    float brightness = dot(normal, surfaceToLight) /
                      (length(surfaceToLight) * length(normal));
    brightness = max(min(brightness,1.0),0.0);

    // Get texture color
    vec4 t_color = vec4(1.0, 1.0, 1.0, 0.3);

    // Final color
    vec4 color = u_color * t_color * mix(v_color, t_color, 0.25);

    if( ori_color < 0.5 ) {
    gl_FragColor = color * brightness * vec4(u_light_intensity, 1);}
    else{
        gl_FragColor = v_color;
    }
}
"""




window = app.Window(width=1024, height=1024,
                    color=(0.30, 0.30, 0.35, 1.00))

@window.event
def on_draw(dt):
    global phi, theta, duration
    window.clear()
    # Filled cube
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
    cube['u_color'] = 1, 1, 1, 1
    cube.draw(gl.GL_TRIANGLES, I)

    # Outlined cube
    gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
    gl.glEnable(gl.GL_BLEND)
    gl.glDepthMask(gl.GL_FALSE)
    cube['u_color'] = 0, 0, 0, 1
    cube.draw(gl.GL_LINES, O)
    gl.glDepthMask(gl.GL_TRUE)

    # Axis
    gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
    gl.glEnable(gl.GL_BLEND)
    gl.glDepthMask(gl.GL_FALSE)
    cube['u_color'] = 1, 1, 1, 1
    cube.draw(gl.GL_LINES, A)
    gl.glDepthMask(gl.GL_TRUE)

    # Rotate cube
    # theta += 0.2 # degrees
    # phi   += 0.0 # degrees
    view = cube['u_view'].reshape(4,4)
    model = np.eye(4, dtype=np.float32)
    glm.rotate(model, theta, 0, 0, 1)
    glm.rotate(model, phi,   1, 0, 0)
    cube['u_model']  = model
    cube['u_normal'] = np.array(np.matrix(np.dot(view, model)).I.T)
    updateZoom(dt)


@window.event
def on_resize(width, height):
    cube['u_projection'] = glm.perspective(45.0, width / float(height), 2.0, 1000.0)

@window.event
def on_init():
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glPolygonOffset(1, 1)
    gl.glEnable(gl.GL_LINE_SMOOTH)

# 键盘按键事件
@window.event
def on_key_press(symbol, modifiers):
    if symbol == 32: #SPACE
        if( converter.convertToPCD() ):
            print("成功转换为pcd文件! 文件大小： " + converter.current_file_size)
        else:
            print("失败，未能转换成功! ")

zoom_vel    =   0 
zoom_factor = -80
zoom_x      =  10
zoom_y      = -30
phi         = 290
theta       =  20

def updateZoom(dt):
    global zoom_factor, zoom_vel, zoom_x, zoom_y, phi, theta
    zoom_factor += zoom_vel * dt
    zoom_vel *= 0.95
    if(abs(zoom_vel) < 0.01):
        zoom_vel = 0.0
    
    cube['u_view']  = glm.translation(zoom_x, zoom_y, zoom_factor)

# 鼠标滚轮事件
@window.event
def on_mouse_scroll(x, y, dx, dy):
    global zoom_factor, zoom_x, zoom_y, zoom_vel
    zoom_vel += 20*dy



# 鼠标移动事件
@window.event
def on_mouse_drag(x, y, dx, dy, button):
    global zoom_x ,zoom_y, zoom_factor, phi, theta
    if button == 2:
        s = abs(zoom_factor) * 0.001
        zoom_x += dx * s
        zoom_y -= dy * s
        cube['u_view']  = glm.translation(zoom_x, zoom_y, zoom_factor)
    
    if button == 8:
        phi   += dy
        theta += dx



V,I,O,A = cubes(converter.renderPoints, 1.0)
cube = gloo.Program(vertex, fragment)
cube.bind(V)

cube["u_light_position"]  = 2,2,2
cube["u_light_intensity"] = 1.3,1.3,1.3
cube['u_model'] = np.eye(4, dtype=np.float32)

cube['u_view']  = glm.translation(zoom_x, zoom_y, zoom_factor)

app.run()