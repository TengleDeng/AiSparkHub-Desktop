(function() {
    // 提取所有笔记
    const notes = Array.from(document.querySelectorAll('.note-card')).map(el => {
        const title = el.querySelector('.note-item-header')?.innerText.trim() || '';
        const contentEl = el.querySelector('.note-content.tiptap-preview');
        let content = contentEl ? contentEl.innerText.trim() : '';
        const tags = Array.from(el.querySelectorAll('.note-tags .tag')).map(tag => tag.innerText.trim()).join(', ');
        const editTime = el.querySelector('.card-bottom-main')?.innerText.trim() || '';
        // 清理文件名
        let filename = title || (content.substring(0, 10) || '未命名');
        filename = filename.replace(/[\\/:*?"<>|]/g, '_');
        // Markdown格式
        const md = `# ${title}\n\n**标签：** ${tags}\n\n**编辑时间：** ${editTime}\n\n---\n\n${content}`;
        return { filename, md };
    });
    // 存入localStorage，供PyQt端读取
    localStorage.setItem('BIJI_EXPORT_MD', JSON.stringify(notes));
    alert('已提取所有笔记内容，请在客户端保存。');
})(); 